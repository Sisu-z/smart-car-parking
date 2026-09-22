"""[EXPERIMENTAL] 保留的标记/IPPE 实验，不属于普通车位线自主泊车验收。
仅处理本地图片，不连接相机或电机；通用标定/变换数学可复用。
输入标定必须匹配原始图片分辨率，禁止自动缩放后仍沿用旧内参。
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np

def object_points(size):
    if not np.isfinite(size) or size<=0: raise ValueError("标记尺寸必须是实测正数，单位 m")
    h=size/2
    return np.array([[-h,h,0],[h,h,0],[h,-h,0],[-h,-h,0]],dtype=np.float64)

def validate_calibration(calibration, shape):
    k=np.array(calibration["camera_matrix"],dtype=float)
    distortion=np.array(calibration["dist_coeffs"],dtype=float)
    if k.shape!=(3,3) or not np.isfinite(k).all() or k[0,0]<=0 or k[1,1]<=0:
        raise ValueError("无效相机内参")
    if distortion.size not in (4,5,8,12,14) or not np.isfinite(distortion).all():
        raise ValueError("无效畸变参数")
    if list(calibration["image_size"])!=[shape[1],shape[0]]:
        raise ValueError("图片分辨率不匹配标定；未自动猜测缩放内参")
    return k,distortion

def solve_pose(corners,size,k,distortion):
    points=object_points(size)
    count,rvecs,tvecs,_=cv2.solvePnPGeneric(points,np.asarray(corners,dtype=np.float64).reshape(4,2),
        k,distortion,flags=cv2.SOLVEPNP_IPPE_SQUARE)
    candidates=[]
    for rv,tv in zip(rvecs,tvecs):
        rot,_=cv2.Rodrigues(rv)
        if not np.isfinite(rot).all() or not np.isfinite(tv).all() or np.any((rot@points.T+tv)[2]<=0): continue
        projected,_=cv2.projectPoints(points,rv,tv,k,distortion)
        error=float(np.sqrt(np.mean(np.sum((projected.reshape(4,2)-np.asarray(corners).reshape(4,2))**2,axis=1))))
        transform=np.eye(4);transform[:3,:3]=rot;transform[:3,3]=tv.ravel()
        candidates.append(dict(reprojection_rmse_px=error,T_camera_tag=transform.tolist()))
    candidates.sort(key=lambda c:c["reprojection_rmse_px"])
    # 平面位姿可能双解；保留候选，不把最低重投影误差等同已消歧。
    ambiguous=len(candidates)>1 and candidates[1]["reprojection_rmse_px"]-candidates[0]["reprojection_rmse_px"]<.5
    return dict(candidates=candidates,ambiguous=ambiguous,
        valid_for_control=bool(candidates) and not ambiguous and candidates[0]["reprojection_rmse_px"]<2)

def detect(image,calibration,tag_size_m,expected_id=None,timestamp_ms=0):
    k,d=validate_calibration(calibration,image.shape)
    dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    detector=cv2.aruco.ArucoDetector(dictionary,cv2.aruco.DetectorParameters())
    corners,ids,_=detector.detectMarkers(image)
    observations=[]
    if ids is not None:
        for marker,c in zip(ids.ravel(),corners):
            if expected_id is not None and int(marker)!=expected_id: continue
            pose=solve_pose(c,tag_size_m,k,d)
            observations.append(dict(timestamp_ms=timestamp_ms,frame_id="camera_optical",
                tag_id=int(marker),corners_px=c.reshape(4,2).tolist(),**pose))
    return observations

def camera_to_vehicle(T_vehicle_camera,T_camera_tag):
    matrices=[np.asarray(m,dtype=float) for m in (T_vehicle_camera,T_camera_tag)]
    for m in matrices:
        if m.shape!=(4,4) or not np.isfinite(m).all() or not np.allclose(m[3],[0,0,0,1]) or \
            not np.allclose(m[:3,:3].T@m[:3,:3],np.eye(3),atol=1e-6) or not np.isclose(np.linalg.det(m[:3,:3]),1):
            raise ValueError("必须显式提供有效的刚性坐标变换")
    return matrices[0]@matrices[1]

def main():
    p=argparse.ArgumentParser(description="本地图片 AprilTag 检测；不连接硬件")
    p.add_argument("image"); p.add_argument("calibration"); p.add_argument("--tag-size-m",type=float,required=True)
    p.add_argument("--id",type=int); p.add_argument("--timestamp-ms",type=int,default=0)
    args=p.parse_args();image=cv2.imread(args.image)
    if image is None: p.error("图片无法读取")
    cal=json.loads(Path(args.calibration).read_text())
    print(json.dumps(detect(image,cal,args.tag_size_m,args.id,args.timestamp_ms),ensure_ascii=False,indent=2))

if __name__=="__main__": main()
