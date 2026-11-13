"""Sensor-only active scanning and a bounded local obstacle memory.

All positions/headings here are command-response estimates, never odometry.
The controller receives no simulator, task goal coordinate or contact data.
"""
from __future__ import annotations

import copy
from dataclasses import asdict,dataclass
import math

import numpy as np

from psi_gw.body.base import Action,Observation
from .motion_profile import MotionProfile
from .robot_controllers import sensor_view
from .validation_io import digest


def angle_delta(a,b):return math.remainder(a-b,2*math.pi)


@dataclass(frozen=True)
class NavigationConfig:
    dt_s: float = .05
    speed_mps: float = .03
    turn_rps: float = .3
    radius_m: float = .17
    margin_m: float = .025
    horizon_m: float = .45
    scan_half_angle: float = .68
    maximum_age_s: float = .4
    point_lifetime_s: float = 28.0

    def __post_init__(self):
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in asdict(self).values()):
            raise ValueError('invalid navigation configuration')
        if self.dt_s!=.05 or self.speed_mps>.03 or self.turn_rps>.3 or not .12<=self.radius_m<=.3:
            raise ValueError('navigation parameters exceed the model envelope')


class ActiveNavigator:
    def __init__(self,profile:MotionProfile,config:NavigationConfig=NavigationConfig()):
        self.profile,self.config=profile,config
        self.position=[0.,0.];self.heading=0.;self.velocity=[0.,0.,0.]
        self.translation_uncertainty=0.;self.heading_uncertainty=0.
        self.history=[];self.points=[];self.rays=[]
        self.last_tick=-1;self.last_fingerprint=None;self.last_action=Action('stop')
        self.last_range_stamp=-1.;self.last_camera_stamp=-1.
        self.last_seen_range_stamp=-1.;self.range_packet_hash=None;self.accepted_range=None
        self.range_source='unknown';self.range_age_s=None
        self.camera_hint=False;self.camera_stamp=-1.;self.camera_bearings=[]
        self.scan_targets=[];self.scan_index=0;self.last_scan_position=[0.,0.];self.last_scan_tick=-10000
        self.travel_angle=0.;self.mode='initial';self.energy_latched=False;self.last_decision={}

    def _advance(self,tick,previous):
        if self.last_tick>=0:
            if tick!=self.last_tick+1:raise ValueError('navigator requires consecutive decision ticks')
            if previous!=self.last_action:raise ValueError('previous action does not match issued command')
            command=previous.params if previous.name=='drive' else {}
            old=self.velocity;new=self.profile.response(old,command,self.config.dt_s)
            local=[(old[i]+new[i])*.5*self.config.dt_s for i in range(3)]
            middle=self.heading+local[2]/2
            co,si=math.cos(middle),math.sin(middle)
            self.position[0]+=co*local[0]-si*local[1]
            self.position[1]+=si*local[0]+co*local[1]
            self.heading+=local[2];self.velocity=new
            relative=.5*self.profile.relative_uncertainty
            self.translation_uncertainty+=math.hypot(*local[:2])*relative+.00002
            self.heading_uncertainty+=abs(local[2])*relative+.00001
        self.history.append(dict(t=tick*self.config.dt_s,x=self.position[0],y=self.position[1],heading=self.heading))
        self.history=self.history[-64:]

    def _pose_at(self,t):
        if not self.history or t<self.history[0]['t']-self.config.maximum_age_s:return None
        if t<=self.history[0]['t']:return self.history[0]
        for a,b in zip(self.history,self.history[1:]):
            if a['t']<=t<=b['t']:
                u=(t-a['t'])/(b['t']-a['t'])
                return {key:a[key]+u*(b[key]-a[key]) for key in ('t','x','y','heading')}
        return self.history[-1] if t<=self.history[-1]['t']+1e-9 else None

    def _timestamp(self,sample,now):
        if not isinstance(sample,dict):return None
        t=sample.get('captured_at_s',now)
        return float(t) if type(t) in (int,float) and math.isfinite(t) and 0<=now-t<=self.config.maximum_age_s+1e-9 else None

    def _sense(self,observation):
        now=observation.tick*self.config.dt_s
        self.points=[p for p in self.points if now-p['t']<=self.config.point_lifetime_s]
        self.rays=[p for p in self.rays if now-p['t']<=24.0]
        sample=observation.sensors.get('ultrasonic');stamp=self._timestamp(sample,now)
        distance=None;reordered=False
        self.range_source='unknown';self.range_age_s=None
        if stamp is not None:
            packet_hash=digest(sample)
            if stamp<self.last_seen_range_stamp:
                reordered=True;stamp=None
            elif stamp==self.last_seen_range_stamp and packet_hash!=self.range_packet_hash:
                stamp=None
            elif stamp>self.last_seen_range_stamp:
                self.last_seen_range_stamp=stamp;self.range_packet_hash=packet_hash
        if stamp is not None and sample.get('status')=='ok':
            v=sample.get('distance_m')
            if type(v) in (int,float) and math.isfinite(v) and .02<=v<=4:
                distance=float(v);self.accepted_range=dict(t=stamp,value=distance)
                self.range_source='measured';self.range_age_s=now-stamp
        if distance is not None and stamp>self.last_range_stamp:
            pose=self._pose_at(stamp)
            if pose is not None:
                heading=pose['heading'];co,si=math.cos(heading),math.sin(heading)
                origin=(pose['x']+.045*co,pose['y']+.045*si)
                # A zero-width echo cannot clear adjacent occupied evidence.
                # Retain endpoints until expiry rather than inventing a free cone.
                if distance<1.3:
                    point=dict(x=origin[0]+co*distance,y=origin[1]+si*distance,t=stamp,distance=distance,
                               anchor_x=pose['x'],anchor_y=pose['y'])
                    self.points=[p for p in self.points if math.hypot(p['x']-point['x'],p['y']-point['y'])>.025]
                    self.points.append(point);self.points=self.points[-512:]
                self.rays.append(dict(t=stamp,heading=heading,distance=distance,x=origin[0],y=origin[1]))
                self.rays=self.rays[-768:];self.last_range_stamp=stamp
        camera=observation.sensors.get('camera');capture=self._timestamp(camera,now)
        if capture is not None and capture>self.last_camera_stamp:
            self.last_camera_stamp=capture
            try:
                if camera.get('encoding','rgb8')!='rgb8':raise ValueError('unsupported image encoding')
                image=np.asarray(camera['rgb'])
                if image.ndim!=3 or image.shape[2]!=3 or image.dtype.kind not in 'iuf' or not np.isfinite(image).all() or image.min()<0 or image.max()>255:raise ValueError('invalid pixels')
                if camera.get('width',image.shape[1])!=image.shape[1] or camera.get('height',image.shape[0])!=image.shape[0]:raise ValueError('image dimensions disagree')
                value=image.max(axis=2)/255
                saturation=(image.max(axis=2)-image.min(axis=2))/np.maximum(image.max(axis=2),1)
                # Colour regions may cue side scans even when the central echo is clear.
                mask=np.zeros(value.shape,dtype=bool)
                mask[int(image.shape[0]*.60):]|=(saturation>.30)[int(image.shape[0]*.60):]
                mask[int(image.shape[0]*.82):]|=(value<.70)[int(image.shape[0]*.82):]
                self.camera_hint=bool(mask.sum()>=2)
                focal=image.shape[1]/(2*math.tan(math.pi/6))
                self.camera_bearings=[math.atan((image.shape[1]/2-(i+.5))/focal) for i in np.flatnonzero(mask.any(axis=0))]
                self.camera_stamp=capture;self.last_camera_stamp=capture
            except (KeyError,TypeError,ValueError):
                self.camera_hint=False;self.camera_bearings=[]
        if now-self.camera_stamp>self.config.maximum_age_s:
            self.camera_hint=False;self.camera_bearings=[]
        if reordered and self.accepted_range is not None and now-self.accepted_range['t']<=self.config.maximum_age_s:
            distance=self.accepted_range['value'];self.range_source='retained_capture';self.range_age_s=now-self.accepted_range['t']
        return distance

    def _clearance(self,angle):
        x,y=self.position;co,si=math.cos(angle),math.sin(angle)
        best=self.config.horizon_m
        for point in self.points:
            dx,dy=point['x']-x,point['y']-y
            along,cross=dx*co+dy*si,-dx*si+dy*co
            age_distance=math.hypot(x-point['anchor_x'],y-point['anchor_y'])
            radius=self.config.radius_m+self.config.margin_m+.025*point['distance']+.12*age_distance
            if math.hypot(dx,dy)<radius and along<0:
                best=min(best,.12)  # Slow escape from an estimated inflated margin.
                continue
            if abs(cross)<radius:
                contact=along-math.sqrt(max(0,radius*radius-cross*cross))
                if along+radius>0:best=min(best,max(0,contact))
        return best

    def _select_direction(self):
        desired=max(-.5,min(.5,-.8*self.position[1]))
        candidates=[]
        for i in range(-12,13):
            angle=i*.1
            clearance=self._clearance(angle)
            if clearance<.08:continue
            # Prefer meaningful forward reach and mild return to the initial line.
            score=clearance*math.cos(angle)-.13*abs(angle-desired)-.04*abs(angle-self.travel_angle)
            candidates.append((score,angle,clearance))
        if not candidates:
            for angle in (-math.pi,-2.5,-2.,-1.6,1.6,2.,2.5,math.pi):
                clearance=self._clearance(angle)
                if clearance>=.08:candidates.append((clearance*math.cos(angle)-.13*abs(angle),angle,clearance))
        return max(candidates) if candidates else None

    def _start_scan(self,tick):
        center=max(-.35,min(.35,self.heading))
        self.scan_targets=[center-self.config.scan_half_angle,center+self.config.scan_half_angle,0.]
        self.scan_index=0;self.mode='scan';self.last_scan_tick=tick

    def choose(self,observation:Observation,previous_action:Action=Action('stop')):
        observation=sensor_view(observation)
        if type(observation.tick) is not int or observation.tick<0:raise ValueError('invalid observation tick')
        fingerprint=digest(dict(observation=asdict(observation),previous=asdict(previous_action)))
        if observation.tick==self.last_tick:
            if fingerprint!=self.last_fingerprint:raise ValueError('conflicting duplicate decision')
            return copy.deepcopy(self.last_action)
        if observation.tick<self.last_tick:raise ValueError('decision clock moved backwards')
        self._advance(observation.tick,previous_action)
        distance=self._sense(observation)
        needs=[observation.internal.get(k) for k in ('hunger','damage')]
        known=all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in needs)
        if known and (needs[0]>=.85 or needs[1]>=.95):self.energy_latched=True
        action=Action('stop')
        if self.energy_latched:self.mode='energy_stop'
        elif not known:self.mode='unknown_needs'
        elif distance is None:self.mode='unknown_range'
        else:
            candidate=self._select_direction()
            danger=candidate is None
            # A known angular region need not be rescanned at a fixed distance.
            # Image bearings only request new sensing; they never add map depth.
            visual_unknown=self.camera_hint and any(not any(
                math.hypot(p['x']-self.position[0],p['y']-self.position[1])<1.4 and
                abs(angle_delta(math.atan2(p['y']-self.position[1],p['x']-self.position[0]),self.heading+b))<.20
                for p in self.points) and not any(
                math.hypot(r['x']-self.position[0],r['y']-self.position[1])<.10 and
                abs(angle_delta(r['heading'],self.heading+b))<.16 and r['distance']>.5
                for r in self.rays) for b in self.camera_bearings)
            moved=math.dist(self.position,self.last_scan_position)
            due=self.last_scan_tick<0 or (observation.tick-self.last_scan_tick>100 and (moved>.18 or danger))
            if not self.scan_targets and (danger or visual_unknown) and due:
                self._start_scan(observation.tick)
            if self.scan_targets:
                error=angle_delta(self.scan_targets[self.scan_index],self.heading)
                if abs(error)<.025:
                    self.scan_index+=1
                    if self.scan_index==len(self.scan_targets):
                        self.scan_targets=[];self.scan_index=0;self.last_scan_position=self.position.copy();self.mode='travel'
                    else:error=angle_delta(self.scan_targets[self.scan_index],self.heading)
                if self.scan_targets:
                    # Slow near endpoints to bound overshoot of the response model.
                    rate=max(-self.config.turn_rps,min(self.config.turn_rps,4*error))
                    action=Action('drive',dict(yaw_rps=rate));self.mode='scan'
            if not self.scan_targets:
                candidate=self._select_direction()
                if candidate is None:
                    self.mode='blocked'
                    if observation.tick-self.last_scan_tick>80:self._start_scan(observation.tick)
                else:
                    _,angle,clearance=candidate;self.travel_angle=angle
                    # Counter-steer estimated heading without consulting actual pose.
                    correction=max(-.12,min(.12,-self.heading*.7))
                    speed=self.config.speed_mps*min(1.,clearance/.25)
                    relative=angle-self.heading
                    action=Action('drive',dict(forward_mps=speed*math.cos(relative),lateral_mps=speed*math.sin(relative),yaw_rps=correction))
                    self.mode='travel'
        self.last_tick=observation.tick;self.last_fingerprint=fingerprint;self.last_action=copy.deepcopy(action)
        self.last_decision=dict(mode=self.mode,estimated_position=self.position.copy(),estimated_heading_rad=self.heading,
            heading_source='identified_command_response_not_odometry',translation_uncertainty_m=self.translation_uncertainty,
            heading_uncertainty_rad=self.heading_uncertainty,obstacle_points=len(self.points),scan_index=self.scan_index,
            camera_sampling_hint=self.camera_hint,range_m=distance,range_source=self.range_source,range_age_s=self.range_age_s,travel_angle_rad=self.travel_angle)
        return action

    def snapshot(self):
        state={k:copy.deepcopy(v) for k,v in self.__dict__.items() if k not in ('profile','config','last_action')}
        return dict(type='psi_gw.picrawler.active_navigator',version=1,profile=self.profile.snapshot(),
                    config=asdict(self.config),last_action=asdict(self.last_action),state=state)

    @classmethod
    def restore(cls,p):
        if p.get('type')!='psi_gw.picrawler.active_navigator' or type(p.get('version')) is not int or p.get('version')!=1:raise ValueError('unsupported navigator snapshot')
        obj=cls(MotionProfile.restore(p['profile']),NavigationConfig(**p['config']))
        if p['state'].keys()!=set(obj.__dict__)-{'profile','config','last_action'}:raise ValueError('invalid navigator state fields')
        digest(p)  # Reject NaN and non-JSON values.
        for k,v in p['state'].items():setattr(obj,k,copy.deepcopy(v))
        obj.last_action=Action(**p['last_action'])
        if len(obj.points)>512 or len(obj.history)>64 or len(obj.rays)>768:raise ValueError('navigator history exceeds bounds')
        if type(obj.scan_index) is not int or (obj.scan_targets and not 0<=obj.scan_index<len(obj.scan_targets)) or (not obj.scan_targets and obj.scan_index!=0):
            raise ValueError('invalid scan index')
        def vector(values,length):
            return isinstance(values,(list,tuple)) and len(values)==length and all(type(v) in (int,float) and math.isfinite(v) for v in values)
        if not vector(obj.position,2) or not vector(obj.velocity,3) or not vector(obj.last_scan_position,2):
            raise ValueError('invalid motion estimate shape')
        if type(obj.last_tick) is not int or obj.last_tick < -1 or type(obj.last_scan_tick) is not int or obj.last_scan_tick>obj.last_tick:
            raise ValueError('invalid navigator clocks')
        for key in ('heading','translation_uncertainty','heading_uncertainty','travel_angle','last_range_stamp','last_camera_stamp','last_seen_range_stamp','camera_stamp'):
            value=getattr(obj,key)
            if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('invalid scalar state')
        if min(obj.translation_uncertainty,obj.heading_uncertainty)<0 or type(obj.energy_latched) is not bool or type(obj.camera_hint) is not bool:
            raise ValueError('invalid uncertainty or flag')
        for rows,fields in ((obj.points,('x','y','t','distance','anchor_x','anchor_y')),
                            (obj.rays,('t','heading','distance','x','y')),
                            (obj.history,('t','x','y','heading'))):
            if not isinstance(rows,list) or any(not isinstance(row,dict) or set(row)!=set(fields) or not vector([row[k] for k in fields],len(fields)) for row in rows):
                raise ValueError('invalid stored sensor or pose history')
        if any(a['t']>=b['t'] for a,b in zip(obj.history,obj.history[1:])):
            raise ValueError('pose history clock is not increasing')
        if obj.history and not math.isclose(obj.history[-1]['t'],obj.last_tick*obj.config.dt_s,abs_tol=1e-9):
            raise ValueError('pose history and controller clock disagree')
        if not vector(obj.scan_targets,len(obj.scan_targets)) or len(obj.scan_targets) not in (0,3):
            raise ValueError('invalid scan targets')
        if obj.last_action.name not in ('drive','stop') or obj.last_action.params.keys()-{'forward_mps','lateral_mps','yaw_rps'}:
            raise ValueError('invalid stored action')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in obj.last_action.params.values()):
            raise ValueError('invalid stored action number')
        if math.hypot(obj.last_action.params.get('forward_mps',0),obj.last_action.params.get('lateral_mps',0))>.03+1e-12 or abs(obj.last_action.params.get('yaw_rps',0))>.3:
            raise ValueError('stored action exceeds bounds')
        return obj
