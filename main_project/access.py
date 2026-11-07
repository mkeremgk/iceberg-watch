"""Geometric access scenarios. These are not observed penguin movements."""
import heapq
import math
import cv2
import numpy as np


def frontier(ribbon, approach):
    """Target cells sharing a side with the approach area; not a water classifier."""
    neighbour = cv2.dilate(approach.astype('uint8'),
                          np.array([[0,1,0],[1,1,1],[0,1,0]], np.uint8)) > 0
    return ribbon & neighbour


def shortest_access(cost, targets, start, spacing_m):
    """Dijkstra on 8 neighbours; corner cutting forbidden; unknown cells are infinite."""
    cost=np.asarray(cost,dtype=float);targets=np.asarray(targets,dtype=bool)
    if cost.shape!=targets.shape or cost.ndim!=2 or not math.isfinite(spacing_m) or spacing_m<=0:
        raise ValueError('Invalid grids or spacing')
    passable=np.isfinite(cost)
    if np.any(passable&(cost<=0)):
        raise ValueError('Finite movement costs must be positive')
    rows,cols=cost.shape
    if not (0<=start[0]<rows and 0<=start[1]<cols):
        return {'status':'start_outside_grid','path':[]}
    if not np.any(targets&passable):
        return {'status':'no_reviewed_open_water_target','path':[]}
    if not passable[start]:
        return {'status':'start_not_on_reviewed_passable_surface','path':[]}
    distance=np.full(cost.shape,np.inf);distance[start]=0
    parent=np.full(cost.shape,-1,dtype=np.int64)
    queue=[(0.,start[0],start[1])]
    # Keep neighbour and heap ordering unchanged, including equal-cost tie breaks.
    moves=[(dr,dc,spacing_m*math.hypot(dr,dc))
           for dr in (-1,0,1) for dc in (-1,0,1) if dr or dc]
    while queue:
        d,r,c=heapq.heappop(queue)
        if d!=distance[r,c]:continue
        if targets[r,c]:
            path=[(r,c)];end=(r,c)
            while path[-1]!=start:
                flat=parent[path[-1]];path.append(divmod(int(flat),cols))
            path.reverse()
            length=sum(math.hypot(b[0]-a[0],b[1]-a[1])*spacing_m for a,b in zip(path,path[1:]))
            return {'status':'model_path_found','path':path,'distance_m':length,'cost':d,'end':end}
        for dr,dc,step_m in moves:
            rr,cc=r+dr,c+dc
            if not (0<=rr<rows and 0<=cc<cols) or not passable[rr,cc]:continue
            if dr and dc and (not passable[r,cc] or not passable[rr,c]):continue
            nd=d+step_m*(cost[r,c]+cost[rr,cc])/2
            if nd<distance[rr,cc]:
                distance[rr,cc]=nd;parent[rr,cc]=r*cols+c
                heapq.heappush(queue,(nd,rr,cc))
    return {'status':'no_path_under_model','path':[]}


def aggregate_masks(environment, review, factor):
    """Any blocked fine pixel blocks its coarse cell; do not open narrow gaps."""
    if environment.shape!=review.shape or factor<1 or environment.shape[0]%factor or environment.shape[1]%factor:
        raise ValueError('Matching grids divisible by factor required')
    h,w=environment.shape
    def blocks(a):return a.reshape(h//factor,factor,w//factor,factor)
    passable=blocks(np.isin(environment,[2,3])&~np.isin(review,[2,3,4,5])).all(axis=(1,3))
    targets=blocks(environment==2).any(axis=(1,3))&passable
    obstacles=blocks(review==1).any(axis=(1,3))
    return passable,targets,obstacles
