import math
import unittest
import cv2
import numpy as np
from offline.vision import detect, solve_pose, object_points, camera_to_vehicle
from offline.parking import collision, Config, plan
from offline.native_motor import NativeMotor

class VisionTests(unittest.TestCase):
    def setUp(self):
        self.k=np.array([[600,0,320],[0,600,240],[0,0,1]],dtype=float)
        self.d=np.zeros(5)
    def test_projected_pose(self):
        r=np.array([2.8,.1,.2]);t=np.array([.1,.04,.8])
        image,_=cv2.projectPoints(object_points(.12),r,t,self.k,self.d)
        pose=solve_pose(image,.12,self.k,self.d)
        self.assertTrue(pose["candidates"])
        actual=np.array(pose["candidates"][0]["T_camera_tag"])
        np.testing.assert_allclose(actual[:3,3],t,atol=1e-6)
        self.assertLess(pose["candidates"][0]["reprojection_rmse_px"],1e-5)
    def test_detect_and_wrong_id(self):
        dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
        marker=cv2.aruco.generateImageMarker(dictionary,7,200)
        image=np.full((480,640),255,dtype=np.uint8);image[140:340,220:420]=marker
        cal=dict(camera_matrix=self.k.tolist(),dist_coeffs=self.d.tolist(),image_size=[640,480])
        found=detect(image,cal,.12,7,100)
        self.assertEqual(len(found),1);self.assertEqual(found[0]["tag_id"],7)
        self.assertEqual(detect(image,cal,.12,8),[])
        self.assertEqual(detect(np.full_like(image,255),cal,.12),[])
        with self.assertRaises(ValueError):detect(image[:240],cal,.12)
    def test_transform_and_validation(self):
        T=np.eye(4);T[0,3]=.3
        np.testing.assert_allclose(camera_to_vehicle(T,np.eye(4)),T)
        bad=T.copy();bad[0,0]=2
        with self.assertRaises(ValueError):camera_to_vehicle(bad,T)
        with self.assertRaises(ValueError):object_points(float("nan"))
    def test_front_parallel_ambiguity(self):
        points,_=cv2.projectPoints(object_points(.12),np.array([math.pi,0,0]),np.array([0.,0.,1.]),self.k,self.d)
        result=solve_pose(points,.12,self.k,self.d)
        self.assertFalse(result["valid_for_control"])

class IntegrationTests(unittest.TestCase):
    def test_motor_timeout_and_no_resume(self):
        m=NativeMotor()
        try:
            for _ in range(100):m.step(.1,.02)
            self.assertGreater(m.rpm,1)
            for _ in range(40):m.step(.1,.02,disconnect=True)
            self.assertEqual(m.fault,1);self.assertEqual(m.duty,0)
            for _ in range(10):m.step(.1,.02)
            self.assertEqual(m.duty,0)
        finally:m.close()
    def test_footprint_not_point(self):
        self.assertTrue(collision((0,0,0),[(.30,0,.03)],Config()))
        self.assertFalse(collision((0,0,0),[(0,1,.03)],Config()))
    def test_blocked_goal(self):
        self.assertEqual(plan((0,0,0),(-1,0,0),[(-1,0,.2)],Config()),[])

if __name__=="__main__":unittest.main()
