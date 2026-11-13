"""Protocol/transport scenarios against the real kinematic body, without a network."""

import copy
import json

import pytest

from psi_gw.body import Action
from psi_gw.body.picrawler.body import PiCrawlerSimBody, SimConfig
from psi_gw.body.picrawler.bridge import (
    BridgeEndpoint,
    InMemoryTransport,
    ProtocolError,
    QueueFull,
    Reply,
    Request,
    StaleObservation,
)
from psi_gw.body.picrawler.world import World


def setup_bridge(*, capacity=16, **endpoint_options):
    body = PiCrawlerSimBody(World((-5, -5, 5, 5)), SimConfig(camera_enabled=False, initial_x_m=0))
    endpoint = BridgeEndpoint(body, **endpoint_options)
    link = InMemoryTransport(endpoint, capacity=capacity)
    session = link.connect("controller")
    return body, endpoint, link, session


def command(session, sequence, now, *, ttl=20, speed=0.02, request_id=None):
    return Request(session, request_id or f"request-{sequence}", sequence, now, now + ttl,
                   Action("drive", {"forward_mps": speed})).to_json()


def collect(link):
    return [Reply.from_json(payload) for payload in link.receive()]


def test_normal_command_executes_once_at_ack_tick_and_then_has_no_retained_velocity():
    body, endpoint, link, session = setup_bridge()
    start_tick = link.tick
    link.send(command(session, 1, start_tick))
    link.step()
    reply, = collect(link)
    assert reply.status == "completed"
    assert reply.execution_tick == start_tick + 1 == body.tick
    assert reply.observation.tick == body.tick
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)
    assert reply.fresh_observation(now_tick=link.tick, max_age_ticks=0, session=session) == body.observe()
    link.step(3)
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)
    assert all(v == 0 for v in body.frame()["command"].values())
    assert endpoint.pending_count == 0


def test_retry_after_delayed_ack_returns_original_reply_without_double_execution():
    body, _, link, session = setup_bridge()
    wire = command(session, 1, link.tick)
    link.send(wire, reply_delay_ticks=3)
    link.step()
    assert link.receive() == []
    execution_tick = body.tick
    link.send(wire)  # Retry the exact message, not a new sequence.
    link.step()
    retry_wire, = link.receive()
    retry = Reply.from_json(retry_wire)
    assert retry.execution_tick == execution_tick
    assert retry.observation.tick == execution_tick
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)
    with pytest.raises(StaleObservation):
        retry.fresh_observation(now_tick=link.tick, max_age_ticks=0)
    link.step(2)
    original_wire, = link.receive()
    assert original_wire == retry_wire
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)


def test_duplicate_in_flight_is_one_queued_action_and_one_completion():
    body, _, link, session = setup_bridge()
    wire = command(session, 1, link.tick)
    link.send(wire)
    link.send(wire)
    link.step()
    replies = collect(link)
    assert len(replies) == 1 and replies[0].status == "completed"
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)


@pytest.mark.parametrize("lost_side", ["request", "reply"])
def test_packet_loss_is_recoverable_by_same_sequence_retry(lost_side):
    body, _, link, session = setup_bridge()
    wire = command(session, 1, link.tick)
    link.send(wire, **{f"drop_{lost_side}": True})
    link.step(2)
    assert link.receive() == []
    assert body.frame()["pose"]["x_m"] == pytest.approx(0 if lost_side == "request" else 0.001)
    link.send(wire)
    link.step()
    reply, = collect(link)
    assert reply.status == "completed"
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)
    assert (link.request_drops, link.reply_drops) == ((1, 0) if lost_side == "request" else (0, 1))


def test_request_delayed_past_deadline_never_moves_body():
    body, endpoint, link, session = setup_bridge(watchdog_ticks=2)
    link.send(command(session, 1, link.tick, ttl=2), request_delay_ticks=3)
    link.step(4)
    reply, = collect(link)
    assert (reply.status, reply.reason, reply.execution_tick) == ("expired", "deadline", None)
    assert body.frame()["pose"]["x_m"] == 0
    assert endpoint.watchdog_tripped


def test_command_age_limit_cannot_be_bypassed_by_a_large_deadline():
    body, _, link, session = setup_bridge(max_command_age_ticks=2)
    link.send(command(session, 1, link.tick, ttl=100), request_delay_ticks=2)
    link.step(3)
    reply, = collect(link)
    assert (reply.status, reply.reason) == ("expired", "stale")
    assert body.frame()["pose"]["x_m"] == 0


def test_deadline_is_rechecked_while_waiting_behind_another_command():
    body, _, link, session = setup_bridge()
    now = link.tick
    link.send(command(session, 1, now, ttl=1))
    link.send(command(session, 2, now, ttl=1))
    link.step(2)
    first, second = collect(link)
    assert first.status == "completed" and first.execution_tick == now + 1
    assert (second.status, second.reason, second.execution_tick) == ("expired", "deadline", None)
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)


def test_completed_retry_after_original_deadline_still_reports_original_execution():
    body, _, link, session = setup_bridge()
    wire = command(session, 1, link.tick, ttl=1)
    link.send(wire)
    link.step()
    original, = link.receive()
    link.step(3)
    link.send(wire)
    link.step()
    assert link.receive() == [original]
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)


def test_pending_or_completed_sequence_cannot_be_reused_with_changed_payload():
    body, endpoint, link, session = setup_bridge()
    first = command(session, 1, link.tick)
    changed = command(session, 1, link.tick, speed=-0.02)
    assert endpoint.receive(first) is None
    conflict = Reply.from_json(endpoint.receive(changed))
    assert (conflict.status, conflict.reason) == ("rejected", "sequence_conflict")
    endpoint.step()
    original = endpoint.receive(first)
    assert Reply.from_json(endpoint.receive(changed)).reason == "sequence_conflict"
    assert endpoint.receive(first) == original
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)


def test_out_of_order_request_is_not_executed_but_can_be_retried_after_the_gap():
    body, _, link, session = setup_bridge()
    first, second = command(session, 1, link.tick), command(session, 2, link.tick)
    link.send(second)
    link.step()
    gap, = collect(link)
    assert gap.reason == "sequence_gap"
    assert body.frame()["pose"]["x_m"] == 0
    link.send(first)
    link.step()
    assert collect(link)[0].status == "completed"
    link.send(second)
    link.step()
    assert collect(link)[0].status == "completed"
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.002)


def test_evicted_reply_does_not_allow_an_old_sequence_to_execute_again():
    body, _, link, session = setup_bridge(reply_cache_size=1)
    first = command(session, 1, link.tick)
    link.send(first)
    link.step()
    link.receive()
    link.send(command(session, 2, link.tick))
    link.step()
    link.receive()
    link.send(first)
    link.step()
    reply, = collect(link)
    assert (reply.status, reply.reason) == ("rejected", "replay_too_old")
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.002)


def test_pending_capacity_rejects_terminally_instead_of_executing_later():
    body, endpoint, link, session = setup_bridge(max_pending=1)
    first, second = command(session, 1, link.tick), command(session, 2, link.tick)
    assert endpoint.receive(first) is None
    refused = endpoint.receive(second)
    assert Reply.from_json(refused).reason == "queue_full"
    endpoint.step()
    assert endpoint.receive(second) == refused
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)
    assert endpoint.receive(command(session, 3, endpoint.tick)) is None
    endpoint.step()
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.002)


def test_transport_queue_is_bounded_and_dropped_overflow_ack_can_be_retried():
    body, _, link, session = setup_bridge(capacity=1)
    first, second = command(session, 1, link.tick), command(session, 2, link.tick)
    link.send(first)
    with pytest.raises(QueueFull):
        link.send(second)
    assert link.queued_counts == (1, 0)
    link.step()
    link.send(second)
    link.step()  # First reply still fills the one-slot return queue.
    assert link.queued_counts == (0, 1)
    assert link.reply_drops == 1
    assert collect(link)[0].sequence == 1
    link.send(second)
    link.step()
    assert collect(link)[0].sequence == 2
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.002)


def test_disconnect_flushes_traffic_and_reconnect_fences_old_actions_and_replies():
    body, endpoint, link, old_session = setup_bridge()
    old_wire = command(old_session, 1, link.tick)
    link.send(old_wire, request_delay_ticks=5)
    link.step()
    link.disconnect()
    assert endpoint.watchdog_tripped
    assert link.queued_counts == (0, 0)
    assert all(v == 0 for v in body.frame()["command"].values())
    with pytest.raises(ConnectionError):
        link.send(old_wire)
    new_session = link.connect("controller")
    assert new_session != old_session
    link.send(old_wire)  # Even an externally retained packet cannot revive it.
    link.send(command(new_session, 1, link.tick))
    link.step()
    old, current = collect(link)
    assert (old.status, old.reason) == ("rejected", "wrong_session")
    assert current.status == "completed" and current.session == new_session
    link.step(8)
    assert link.receive() == []
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)


def test_reconnect_discards_an_ack_delayed_from_the_previous_connection():
    _, _, link, old_session = setup_bridge()
    link.send(command(old_session, 1, link.tick), reply_delay_ticks=10)
    link.step()
    assert link.queued_counts == (0, 1)
    new_session = link.connect("controller")
    assert new_session != old_session
    link.step(12)
    assert link.receive() == []


def test_telemetry_and_duplicate_retries_do_not_renew_the_command_watchdog():
    body, endpoint, link, session = setup_bridge(watchdog_ticks=2)
    drive = command(session, 1, link.tick)
    link.send(drive)
    link.step()
    link.receive()
    assert not endpoint.watchdog_tripped
    link.send(drive)
    link.step()
    link.receive()
    assert not endpoint.watchdog_tripped
    request = Request(session, "telemetry", 2, link.tick, link.tick + 2)
    link.send(request.to_json())
    link.step()
    reply, = collect(link)
    assert reply.status == "completed" and reply.execution_tick is None
    assert reply.operation == "observe"
    assert endpoint.watchdog_tripped
    assert body.frame()["pose"]["x_m"] == pytest.approx(0.001)
    assert all(v == 0 for v in body.frame()["command"].values())
    link.send(command(session, 3, link.tick))
    link.step()
    assert not endpoint.watchdog_tripped


def test_body_speed_limit_rejection_is_an_ack_and_a_stop_tick():
    body, _, link, session = setup_bridge()
    start = link.tick
    link.send(command(session, 1, start, speed=100))
    link.step()
    reply, = collect(link)
    assert (reply.status, reply.reason, reply.execution_tick) == ("rejected", "invalid_action", None)
    assert body.tick == start + 1
    assert body.frame()["pose"]["x_m"] == 0
    assert all(v == 0 for v in body.frame()["command"].values())


def test_future_issue_tick_is_rejected_without_motion():
    body, _, link, session = setup_bridge()
    link.send(command(session, 1, link.tick + 2))
    link.step()
    assert collect(link)[0].reason == "future_tick"
    assert body.frame()["pose"]["x_m"] == 0


def test_reply_freshness_checks_time_session_and_returns_detached_data():
    _, _, link, session = setup_bridge()
    link.send(command(session, 1, link.tick))
    link.step()
    reply, = collect(link)
    observation = reply.fresh_observation(now_tick=link.tick, max_age_ticks=0, session=session)
    observation.sensors.clear()
    assert "ultrasonic" in reply.observation.sensors
    with pytest.raises(ProtocolError, match="another session"):
        reply.fresh_observation(now_tick=link.tick, max_age_ticks=0, session="another-session")
    with pytest.raises(ProtocolError, match="future"):
        reply.fresh_observation(now_tick=link.tick - 1, max_age_ticks=5)
    with pytest.raises(StaleObservation):
        reply.fresh_observation(now_tick=link.tick + 3, max_age_ticks=2)


def valid_request_data():
    return json.loads(command("session:1", 1, 1))


@pytest.mark.parametrize("field,value", [
    ("version", 2), ("version", True), ("kind", "action"), ("operation", "execute"),
    ("session", ""), ("session", None), ("session", "contains space"),
    ("request_id", "x" * 65), ("sequence", 0), ("sequence", -1), ("sequence", True),
    ("sequence", 2**53), ("issued_tick", -1), ("issued_tick", 1.5),
    ("deadline_tick", 0), ("deadline_tick", False), ("action", None),
    ("unexpected", 1),
])
def test_request_envelope_rejects_invalid_data(field, value):
    data = valid_request_data()
    data[field] = value
    with pytest.raises(ProtocolError):
        Request.from_json(json.dumps(data))


@pytest.mark.parametrize("action", [
    {"name": "jump", "params": {}}, {"name": "stop", "params": {"forward_mps": 0}},
    {"name": "drive", "params": {"motor": 1}}, {"name": "drive", "params": []},
    {"name": "drive", "params": {"forward_mps": True}},
    {"name": "drive", "params": {"forward_mps": float("nan")}},
    {"name": "drive", "params": {"forward_mps": float("inf")}},
    {"name": "drive", "params": {"forward_mps": 10**500}},
    {"name": "drive", "params": {}, "extra": 1},
])
def test_request_action_schema_is_strict(action):
    data = valid_request_data()
    data["action"] = action
    with pytest.raises(ProtocolError):
        Request.from_json(json.dumps(data))


@pytest.mark.parametrize("payload", ["[]", "null", "{", '{"version":1,"version":1}', "\ud800", " " * 16_385])
def test_invalid_or_ambiguous_json_is_rejected(payload):
    with pytest.raises(ProtocolError):
        Request.from_json(payload)


def test_nested_duplicate_keys_and_mutated_action_data_are_rejected():
    wire = command("session:1", 1, 1)
    duplicate = wire.replace('"forward_mps":0.02', '"forward_mps":0.02,"forward_mps":0.03')
    with pytest.raises(ProtocolError):
        Request.from_json(duplicate)
    request = Request.from_json(wire)
    request.action.params["forward_mps"] = float("nan")
    with pytest.raises(ProtocolError):
        request.to_json()


@pytest.fixture
def reply_data():
    _, _, link, session = setup_bridge()
    link.send(command(session, 1, link.tick))
    link.step()
    return json.loads(link.receive()[0])


@pytest.mark.parametrize("field,value", [
    ("version", True), ("version", 2), ("status", []), ("status", "accepted"),
    ("sequence", 0), ("server_tick", -1), ("execution_tick", None),
    ("execution_tick", 1000), ("reason", "queue_full"), ("extra", 0),
])
def test_ack_envelope_is_strict(reply_data, field, value):
    reply_data[field] = value
    with pytest.raises(ProtocolError):
        Reply.from_json(json.dumps(reply_data))


@pytest.mark.parametrize("change", [
    {"tick": -1}, {"tick": 999}, {"internal": {"battery": float("nan")}},
    {"sensors": {"ultrasonic": {"distance_m": 1, "status": "dropout"}}},
    {"sensors": {"ultrasonic": {"distance_m": None, "status": "ok"}}},
    {"sensors": {"ultrasonic": {"distance_m": -1, "status": "ok"}}},
    {"sensors": {"ultrasonic": {"distance_m": True, "status": "ok"}}},
    {"sensors": {"ultrasonic": {"distance_m": None, "status": "mystery"}}},
    {"sensors": {"ultrasonic": {"distance_m": None, "status": "out_of_range"}, "ground_truth": {}}},
])
def test_observation_schema_rejects_invalid_or_undeclared_data(reply_data, change):
    reply_data["observation"].update(change)
    with pytest.raises(ProtocolError):
        Reply.from_json(json.dumps(reply_data))


@pytest.mark.parametrize("camera", [
    {"encoding": "rgb8", "width": 1, "height": 1, "rgb": [[[1, 2, 256]]]},
    {"encoding": "rgb8", "width": 1, "height": 1, "rgb": [[[1, 2, True]]]},
    {"encoding": "rgb8", "width": 1, "height": 1, "rgb": [[[1, 2]]]},
    {"encoding": "rgb8", "width": 2, "height": 1, "rgb": [[[1, 2, 3]]]},
    {"encoding": "rgb8", "width": True, "height": 1, "rgb": [[[1, 2, 3]]]},
    {"encoding": "png", "width": 1, "height": 1, "rgb": [[[1, 2, 3]]]},
])
def test_camera_wire_data_has_an_exact_bounded_rgb_shape(reply_data, camera):
    reply_data["observation"]["sensors"]["camera"] = camera
    with pytest.raises(ProtocolError):
        Reply.from_json(json.dumps(reply_data))


def test_real_camera_observation_round_trips_without_extra_truth_fields():
    body = PiCrawlerSimBody(config=SimConfig(camera_enabled=True))
    endpoint = BridgeEndpoint(body)
    session = endpoint.connect("camera-client")
    request = Request(session, "read", 1, endpoint.tick, endpoint.tick + 2)
    endpoint.receive(request.to_json())
    wire, = endpoint.step()
    reply = Reply.from_json(wire)
    assert reply.observation == body.observe()
    assert set(reply.observation.sensors) == {"ultrasonic", "camera", "telemetry"}
    assert reply.observation.sensors["telemetry"]["source"] == "simulated"
    assert reply.to_json() == wire


@pytest.mark.parametrize("field,value", [
    ("source", "measured"), ("state_of_charge", 1.1), ("power_w", -1),
    ("powered", 1), ("core_voltage_v", 1.2), ("shutdown_reason", "unknown"),
    ("history", {"undervoltage": False, "thermal_throttled": 1}),
])
def test_energy_extension_preserves_simulated_provenance_and_typed_values(reply_data, field, value):
    reply_data["observation"]["sensors"]["telemetry"][field] = value
    with pytest.raises(ProtocolError):
        Reply.from_json(json.dumps(reply_data))


def test_unknown_need_inputs_remain_unknown_across_the_wire(reply_data):
    reply_data["observation"]["internal"] = {"hunger": None, "damage": None}
    reply = Reply.from_json(json.dumps(reply_data))
    assert reply.observation.internal == {"hunger": None, "damage": None}
    assert json.loads(reply.to_json())["observation"]["internal"] == {"hunger": None, "damage": None}


def test_malformed_traffic_does_not_change_body_or_reserve_sequence():
    body, endpoint, link, session = setup_bridge()
    before = copy.deepcopy(body.snapshot())
    with pytest.raises(ProtocolError):
        endpoint.receive('{"sequence":true}')
    assert body.snapshot() == before
    assert endpoint.session == session
    link.send(command(session, 1, link.tick))
    link.step()
    assert collect(link)[0].status == "completed"


def test_unexpected_execution_failure_fences_the_session_and_discards_pending_work():
    body, endpoint, link, session = setup_bridge()
    original_act = body.act

    def fail(action):
        if action.name == "drive":
            raise RuntimeError("simulated endpoint failure")
        original_act(action)

    body.act = fail
    first = command(session, 1, link.tick)
    endpoint.receive(first)
    endpoint.receive(command(session, 2, link.tick))
    with pytest.raises(RuntimeError, match="endpoint failure"):
        endpoint.step()
    assert endpoint.session is None and endpoint.pending_count == 0 and endpoint.watchdog_tripped
    assert Reply.from_json(endpoint.receive(first)).reason == "wrong_session"
    assert body.frame()["pose"]["x_m"] == 0


@pytest.mark.parametrize("failure", ["observation", "validation", "serialization"])
def test_failed_ack_after_execution_preserves_committed_energy_and_fences_retries(monkeypatch, failure):
    body, endpoint, link, session = setup_bridge()
    first = command(session, 1, link.tick)
    link.send(first)
    link.send(command(session, 2, link.tick))
    before = body.snapshot()
    original_observe = body.observe

    def unavailable(*args, **kwargs):
        raise RuntimeError("ACK unavailable")

    def invalid_observation():
        observation = original_observe()
        observation.sensors["telemetry"]["core_voltage_v"] = 1.2
        return observation

    with monkeypatch.context() as fault:
        if failure == "observation":
            fault.setattr(body, "observe", unavailable)
        elif failure == "validation":
            fault.setattr(body, "observe", invalid_observation)
        else:
            fault.setattr(Reply, "to_json", unavailable)
        error_type = ProtocolError if failure == "validation" else RuntimeError
        with pytest.raises(error_type):
            link.step()

    committed = body.snapshot()
    assert committed["tick"] == before["tick"] + 1
    assert committed["pose"][0] - before["pose"][0] == pytest.approx(0.001)
    assert committed["energy"]["energy_consumed_j"] > before["energy"]["energy_consumed_j"]
    assert committed["energy"]["state_of_charge"] < before["energy"]["state_of_charge"]
    assert PiCrawlerSimBody.restore(json.loads(json.dumps(committed))).snapshot() == committed
    assert endpoint.session is None and endpoint.pending_count == 0
    assert endpoint.watchdog_tripped and not link.connected
    assert link.receive() == []  # The uncertain outcome is not replaced by a fabricated ACK.
    with pytest.raises(ConnectionError):
        link.send(first)
    assert Reply.from_json(endpoint.receive(first)).reason == "wrong_session"
    assert body.snapshot() == committed  # A rejected retry does not undo or repeat the tick.
    assert endpoint.step() == []
    assert body.frame()["pose"]["x_m"] == committed["pose"][0]
    assert all(value == 0 for value in body.frame()["command"].values())


def test_failed_expired_pending_ack_fences_remaining_work_before_any_tick(monkeypatch):
    body, endpoint, _, session = setup_bridge()
    now = endpoint.tick
    first = command(session, 1, now, ttl=1)
    expired = command(session, 2, now, ttl=1)
    endpoint.receive(first)
    endpoint.receive(expired)
    endpoint.receive(command(session, 3, now, ttl=10))
    assert Reply.from_json(endpoint.step()[0]).status == "completed"
    assert endpoint.pending_count == 2
    before = body.snapshot()

    def unavailable():
        raise RuntimeError("expired ACK unavailable")

    with monkeypatch.context() as fault:
        fault.setattr(body, "observe", unavailable)
        with pytest.raises(RuntimeError, match="expired ACK unavailable"):
            endpoint.step()

    assert body.snapshot() == before
    assert endpoint.session is None and endpoint.pending_count == 0 and endpoint.watchdog_tripped
    assert Reply.from_json(endpoint.receive(expired)).reason == "wrong_session"
    assert Reply.from_json(endpoint.receive(first)).reason == "wrong_session"
    assert endpoint.step() == []
    assert body.frame()["pose"]["x_m"] == before["pose"][0]


def test_failed_immediate_ack_fences_a_reserved_sequence_without_advancing_energy(monkeypatch):
    body, endpoint, _, session = setup_bridge()
    future = command(session, 1, endpoint.tick + 1)
    before = body.snapshot()

    def unavailable():
        raise RuntimeError("immediate ACK unavailable")

    with monkeypatch.context() as fault:
        fault.setattr(body, "observe", unavailable)
        with pytest.raises(RuntimeError, match="immediate ACK unavailable"):
            endpoint.receive(future)

    assert body.snapshot() == before
    assert endpoint.session is None and endpoint.pending_count == 0 and endpoint.watchdog_tripped
    assert Reply.from_json(endpoint.receive(future)).reason == "wrong_session"
