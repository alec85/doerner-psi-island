"""Relative camera yaw during stationary scans; no model pose or translation.

The scene and camera intrinsics are assumed unchanged. Uninformative or
ambiguous images supply no correction. This is not general visual odometry.
"""
from __future__ import annotations

import copy
import math

import numpy as np

from psi_gw.body.base import Action
from .active_navigation import ActiveNavigator,NavigationConfig
from .motion_profile import MotionProfile
from .robot_controllers import sensor_view
from .validation_io import digest
from dataclasses import asdict


def _image(sample):
    if not isinstance(sample,dict) or sample.get('encoding','rgb8')!='rgb8':return None
    try:
        rgb=np.asarray(sample['rgb'],dtype=float)
        if rgb.ndim!=3 or rgb.shape[2]!=3 or not 4<=rgb.shape[1]<=320 or not 4<=rgb.shape[0]<=240:return None
        if not np.isfinite(rgb).all() or rgb.min()<0 or rgb.max()>255:return None
        if sample.get('width',rgb.shape[1])!=rgb.shape[1] or sample.get('height',rgb.shape[0])!=rgb.shape[0]:return None
        return rgb
    except (TypeError,ValueError,KeyError):return None


def match_yaw(reference,current):
    """Return a gated pinhole horizontal registration, or None (uninformative).

    Chromatic column profiles reduce sensitivity to small vertical gait motion.
    Confidence thresholds are technical heuristics, not statistical intervals.
    """
    a,b=_image(reference),_image(current)
    if a is None or b is None or a.shape!=b.shape:return None
    h,w,_=a.shape;focal=w/(2*math.tan(math.pi/6));columns=np.arange(w)
    profiles=[]
    for image in (a,b):
        profile=image[:max(2,round(h*.75))].mean(axis=0)
        profiles.append(profile)
    a,b=profiles
    ca=a/np.maximum(a.sum(axis=1,keepdims=True),1);b=b/np.maximum(b.sum(axis=1,keepdims=True),1)
    if min(float(ca.std(axis=0).mean()),float(b.std(axis=0).mean()))<.025:return None
    angles=np.arctan((w/2-(columns+.5))/focal)
    offsets=np.linspace(-.30,.30,121);costs=[]
    for offset in offsets:
        source=w/2-focal*np.tan(angles+offset)-.5
        valid=(source>=0)&(source<=w-1)
        if valid.sum()<w*.65:costs.append(1.);continue
        warped=np.stack([np.interp(source[valid],columns,a[:,i]) for i in range(3)],axis=1)
        warped=warped/np.maximum(warped.sum(axis=1,keepdims=True),1)
        costs.append(float(np.abs(warped-b[valid]).mean()))
    best=int(np.argmin(costs));offset=float(offsets[best]);cost=costs[best]
    separated=[c for i,c in enumerate(costs) if abs(offsets[i]-offset)>.10]
    margin=min(separated)-cost if separated else 0.
    if best in (0,len(offsets)-1) or cost>.035 or margin<.004:return None
    return dict(delta_yaw_rad=offset,cost=cost,margin=margin,source='relative_stationary_rgb_registration')


class VisualNavigator(ActiveNavigator):
    _visual_fields=('visual_reference','visual_camera','visual_updates','visual_attempts','visual_last')

    def __init__(self,profile:MotionProfile,config:NavigationConfig=NavigationConfig()):
        super().__init__(profile,config)
        self.visual_reference=None;self.visual_camera=None
        self.visual_updates=0;self.visual_attempts=0;self.visual_last=None

    def _align(self):
        reference=self.visual_reference;current=self.visual_camera
        self.visual_reference=None
        if reference is None or current is None:return None
        if math.dist(self.position,reference['position'])>.05:return None
        result=match_yaw(reference['sample'],current['sample']);self.visual_attempts+=1
        if result is None:
            self.visual_last=dict(accepted=False,reason='uninformative_or_ambiguous')
            return None
        pose=self._pose_at(current['t'])
        if pose is None:return None
        correction=reference['heading']+result['delta_yaw_rad']-pose['heading']
        if abs(correction)>.25:
            self.visual_last=dict(accepted=False,reason='correction_exceeds_gate',correction_rad=correction)
            return None
        self.heading+=correction
        for pose in self.history:
            if pose['t']>=current['t']:pose['heading']+=correction
        # Correct only endpoints acquired since the visual measurement epoch.
        for point in self.points:
            if point['t']>=current['t']:
                dx,dy=point['x']-point['anchor_x'],point['y']-point['anchor_y']
                co,si=math.cos(correction),math.sin(correction)
                point['x']=point['anchor_x']+co*dx-si*dy
                point['y']=point['anchor_y']+si*dx+co*dy
        self.visual_updates+=1;self.visual_last=dict(accepted=True,correction_rad=correction,**result)
        return correction

    def _start_scan(self,tick):
        # A completed sweep may immediately request another one when blocked.
        self._align()
        super()._start_scan(tick)
        if self.visual_camera is not None:
            pose=self._pose_at(self.visual_camera['t'])
            if pose is not None:
                self.visual_reference=dict(sample=copy.deepcopy(self.visual_camera['sample']),
                    heading=pose['heading'],position=self.position.copy(),t=self.visual_camera['t'])

    def choose(self,observation,previous_action=Action('stop')):
        if observation.tick==self.last_tick:return super().choose(observation,previous_action)
        clean=sensor_view(observation)
        if type(observation.tick) is not int or observation.tick<0:raise ValueError('invalid observation tick')
        if self.last_tick>=0 and (observation.tick!=self.last_tick+1 or previous_action!=self.last_action):
            return super().choose(observation,previous_action)
        digest(dict(observation=asdict(clean),previous=asdict(previous_action)))
        sample=clean.sensors.get('camera')
        capture=self._timestamp(sample,observation.tick*self.config.dt_s)
        self.visual_camera=dict(sample=copy.deepcopy(sample),t=capture) if capture is not None and _image(sample) is not None else None
        scanning=bool(self.scan_targets)
        action=super().choose(clean,previous_action)
        if scanning and not self.scan_targets:
            correction=self._align()
            if correction is not None and action.name=='drive':
                params=action.params.copy()
                vx,vy=params.get('forward_mps',0),params.get('lateral_mps',0)
                co,si=math.cos(correction),math.sin(correction)
                params.update(forward_mps=co*vx+si*vy,lateral_mps=-si*vx+co*vy,
                              yaw_rps=max(-.12,min(.12,-self.heading*.7)))
                action=Action('drive',params);self.last_action=copy.deepcopy(action)
        self.last_decision.update(estimated_heading_rad=self.heading,visual_updates=self.visual_updates,
                                 visual_attempts=self.visual_attempts,visual_last=copy.deepcopy(self.visual_last))
        return action

    def snapshot(self):
        base=super().snapshot()
        visual={key:base['state'].pop(key) for key in self._visual_fields}
        return dict(type='psi_gw.picrawler.visual_navigator',version=1,base=base,visual=visual)

    @classmethod
    def restore(cls,p):
        if p.get('type')!='psi_gw.picrawler.visual_navigator' or type(p.get('version')) is not int or p.get('version')!=1:raise ValueError('unsupported visual navigator')
        base=ActiveNavigator.restore(p['base']);obj=cls(base.profile,base.config)
        obj.__dict__.update(base.__dict__)
        if set(p['visual'])!=set(cls._visual_fields):raise ValueError('invalid visual state fields')
        digest(p)
        for key,value in p['visual'].items():setattr(obj,key,copy.deepcopy(value))
        for key in ('visual_updates','visual_attempts'):
            if type(getattr(obj,key)) is not int or getattr(obj,key)<0:raise ValueError('invalid visual counter')
        return obj
