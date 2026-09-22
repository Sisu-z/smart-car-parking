"""复用 OpenCV 的棋盘标定；只接受已有图片，不访问摄像头。
uv run python tools/calibrate_camera.py images --columns 9 --rows 6 --square-m 0.02 --output calibration.json
columns/rows 是内角点数量；square-m 必须实测，不是默认棋盘规格。
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("images");p.add_argument("--columns",type=int,required=True);p.add_argument("--rows",type=int,required=True)
    p.add_argument("--square-m",type=float,required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    if min(a.columns,a.rows)<3 or not np.isfinite(a.square_m) or a.square_m<=0:p.error("棋盘参数无效")
    output=Path(a.output)
    if output.exists():p.error("输出已存在，选择新路径，避免覆盖已有标定")
    model=np.zeros((a.columns*a.rows,3),np.float32)
    model[:,:2]=np.mgrid[0:a.columns,0:a.rows].T.reshape(-1,2)*a.square_m
    objects=[];corners=[];files=[];rejected=[];size=None
    for file in sorted(Path(a.images).iterdir()):
        if file.suffix.lower() not in (".png",".jpg",".jpeg"):continue
        image=cv2.imread(str(file),cv2.IMREAD_GRAYSCALE)
        if image is None:rejected.append(str(file));continue
        this_size=(image.shape[1],image.shape[0])
        if size and size!=this_size:p.error("混合分辨率图片，拒绝混用标定")
        size=this_size
        ok,pts=cv2.findChessboardCornersSB(image,(a.columns,a.rows))
        if not ok:rejected.append(str(file));continue
        objects.append(model.copy());corners.append(pts);files.append(str(file))
    if len(files)<6:p.error(f"仅 {len(files)} 张有效棋盘图片；至少需要 6 张不同视角，实际还应检查覆盖度")
    rms,k,d,rvecs,tvecs=cv2.calibrateCamera(objects,corners,size,None,None)
    errors=[]
    for obj,img,rv,tv in zip(objects,corners,rvecs,tvecs):
        projected,_=cv2.projectPoints(obj,rv,tv,k,d)
        errors.append(float(np.sqrt(np.mean(np.sum((projected-img)**2,axis=2)))))
    result=dict(status="UNVERIFIED：需要独立图片与距离实测复核，低重投影误差不等于准确标定",
        image_size=size,camera_matrix=k.tolist(),dist_coeffs=d.ravel().tolist(),rms_px=rms,
        per_image_rmse_px=errors,used_images=files,rejected_images=rejected,square_m=a.square_m,
        board_inner_corners=[a.columns,a.rows])
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(f"已生成 {output}；{len(files)} 张图；RMS={rms:.3f}px；尚需独立验证")

if __name__=="__main__":main()
