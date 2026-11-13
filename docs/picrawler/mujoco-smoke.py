"""Record physical peripheral/bridge smoke checks and native MuJoCo views.

Run with MUJOCO_GL=egl and the optional MuJoCo extra. PNG encoding uses stdlib.
This is a model render, not an HTML/browser layout acceptance.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import zlib

import mujoco

from psi_gw.body.base import Action
from psi_gw.body.picrawler.bridge import BridgeEndpoint, InMemoryTransport, Request, Reply
from psi_gw.body.picrawler.mujoco_body import MujocoBody
from psi_gw.body.picrawler.mujoco_experiment import metadata
from psi_gw.body.picrawler.replay import write_replay
from psi_gw.body.picrawler.validation_io import source_info, write_json


def png(path, rgb):
    h,w,_=rgb.shape
    def chunk(kind, data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    data=b''.join(b'\0'+row.tobytes() for row in rgb)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',w,h,8,2,0,0,0))+
                          chunk(b'IDAT',zlib.compress(data))+chunk(b'IEND',b''))


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    b=MujocoBody()
    frames=[b.frame()]
    actions={1:Action('led',{'on':True}),5:Action('tone',{'hz':440,'duration_s':.5}),
             20:Action('speak',{'text':'MuJoCo Modelltest','duration_s':.5}),
             40:Action('sound',{'id':'beep','duration_s':.2}),60:Action('led',{'on':False})}
    for tick in range(1,81):
        if tick==12:b.inject_button('user',True)
        if tick==15:b.inject_button('user',False)
        if tick==50:b.inject_button('reset',True)
        if tick==53:b.inject_button('reset',False)
        b.act(actions.get(tick,Action('stand')))
        frames.append(b.frame())
    assert frames[1]['peripherals']['user_led']
    assert frames[5]['peripherals']['speaker']['playing']
    assert frames[12]['peripherals']['user_button_down']
    assert not frames[15]['peripherals']['user_button_down']
    assert frames[50]['peripherals']['reset_button_down']
    assert not frames[-1]['peripherals']['speaker']['playing']
    assert not frames[-1]['peripherals']['user_led']
    write_replay(output/'peripherals.html',frames,metadata(b,'MuJoCo: Lautsprecher, LED und Taster'))
    link=InMemoryTransport(BridgeEndpoint(b));session=link.connect('mujoco-smoke')
    command=Request(session,'drive-1',1,link.tick,link.tick+20,Action('drive',{'forward_mps':.02})).to_json()
    link.send(command);link.step();reply,=link.receive();parsed=Reply.from_json(reply)
    assert parsed.status=='completed' and parsed.observation==b.observe()
    link.send(command);link.step();retry,=link.receive();assert retry==reply
    link.step(7);assert link.endpoint.watchdog_tripped
    assert not any(b.frame()['command'].values())
    link.disconnect()
    renders=[]
    for name,action,ticks in [('stand',Action('stand'),40),('walk',Action('drive',{'forward_mps':.02}),93),('turn',Action('drive',{'yaw_rps':.15}),83)]:
        model=MujocoBody(camera_config=None)
        for _ in range(40): model.act(Action('stand'))
        for _ in range(ticks):model.act(action)
        camera=mujoco.MjvCamera();mujoco.mjv_defaultCamera(camera)
        camera.lookat[:]=model.data.qpos[:3];camera.distance=.55;camera.azimuth=130;camera.elevation=-25
        renderer=mujoco.Renderer(model.model,height=480,width=640)
        renderer.update_scene(model.data,camera=camera)
        rgb=renderer.render();png(output/(name+'.png'),rgb);renderer.close()
        renders.append(dict(name=name,frame=model.frame(include_camera=False)))
    report=dict(source=source_info(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                renderer='MuJoCo 3.3.7 EGL',peripheral_frames=len(frames),peripheral_assertions=True,
                bridge_completion_retry_watchdog_disconnect=True,renders=renders,browser_visual_acceptance=False)
    write_json(output/'smoke.json',report)
    print('Physical peripheral, bridge and native rendering checks passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
