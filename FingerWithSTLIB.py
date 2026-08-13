# -*- coding: utf-8 -*-

import Sofa
import Sofa.Core
import SofaRuntime  
import os 
import math

# --- KHÔNG SỬ DỤNG ĐƯỜNG DẪN TUYỆT ĐỐI ---
# Lấy đường dẫn thư mục hiện tại đang chứa file code này
base_dir = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base_dir, 'mesh') + '/'
result_path = os.path.join(base_dir, 'results') + '/'

# Tự động tạo thư mục 'results' nếu trên máy chưa có
if not os.path.exists(result_path):
    os.makedirs(result_path)

from stlib3.scene import Scene
from stlib3.physics.deformable import ElasticMaterialObject
from stlib3.visuals import VisualModel

# ===== CHIP ĐIỀU KHIỂN TỰ ĐỘNG =====
class AutoFlexController(Sofa.Core.Controller):
    def __init__(self, *args, **kwargs):
        Sofa.Core.Controller.__init__(self, *args, **kwargs)
        self.actuator = kwargs.get('actuator')
        self.time = 0.0

    def onAnimateBeginEvent(self, event):
        self.time += event['dt']
        speed = 2.0 
        
        # ---> [VỊ TRÍ THAY ĐỔI THAM SỐ 1]: Kéo giãn cáp (Cable displacement) <---
        max_pull = 40.0 
        
        pull_value = (max_pull / 2.0) * (1.0 - math.cos(self.time * speed))
        
        if self.actuator is not None:
            self.actuator.value = [pull_value]
# ===================================

def createScene(rootNode):
    # --- THIẾT LẬP SOLVER (Solver Configuration) ---
    rootNode.addObject("RequiredPlugin", name="req_softrobots", pluginName="SoftRobots")
    rootNode.addObject("RequiredPlugin", name="req_mapping", pluginName="Sofa.Component.Mapping.Linear")
    rootNode.addObject("RequiredPlugin", name="req_state", pluginName="Sofa.Component.StateContainer")
    rootNode.addObject("RequiredPlugin", name="req_core", pluginName=[
        "Sofa.Component.AnimationLoop",
        "Sofa.Component.Constraint.Lagrangian.Correction",
        "Sofa.Component.Constraint.Lagrangian.Solver",
        "Sofa.Component.Engine.Select",
        "Sofa.Component.IO.Mesh",
        "Sofa.Component.LinearSolver.Direct",
        "Sofa.Component.Mass",
        "Sofa.Component.ODESolver.Backward",
        "Sofa.Component.SolidMechanics.FEM.Elastic",
        "Sofa.Component.SolidMechanics.Spring",
        "Sofa.Component.Topology.Container.Dynamic",
        "Sofa.Component.Visual",
        "Sofa.GL.Component.Rendering3D"
    ])
    
    scene = Scene(rootNode, gravity=[0.0, -9810.0, 0.0], dt=0.01)
    scene.VisualStyle.displayFlags = 'showBehavior'

    rootNode.addObject("FreeMotionAnimationLoop")
    rootNode.addObject('DefaultVisualManagerLoop')
    rootNode.addObject("BlockGaussSeidelConstraintSolver", maxIterations=1000, tolerance=0.001)

    # --- KHAI BÁO HÌNH HỌC VÀ VẬT LIỆU (Geometry & Material) ---
    # ---> [VỊ TRÍ THAY ĐỔI THAM SỐ 2]: Độ cứng vật liệu (Young's Modulus) <---
    finger = ElasticMaterialObject(name="finger",
                                   volumeMeshFileName=path + "finger.vtk",
                                   poissonRatio=0.45,
                                   youngModulus=400,
                                   totalMass=0.05)
    rootNode.addChild(finger)

    # --- ĐIỀU KIỆN BIÊN (Boundary Conditions) ---
    finger.addObject('BoxROI', name='ROI1', box=[-15, 0, 0, 5, 10, 15], drawBoxes=True)
    finger.addObject('RestShapeSpringsForceField', points='@ROI1.indices', stiffness=1e12)

    # --- ACTUATION HOẶC TẢI NGOÀI (Cable Actuation) ---
    cable = finger.addChild('cable')
    cable.addObject('MechanicalObject',
                    position=[
                        [-17.5, 12.5, 2.5], [-32.5, 12.5, 2.5], [-47.5, 12.5, 2.5],
                        [-62.5, 12.5, 2.5], [-77.5, 12.5, 2.5], [-83.5, 12.5, 4.5],
                        [-85.5, 12.5, 6.5], [-85.5, 12.5, 8.5], [-83.5, 12.5, 10.5],
                        [-77.5, 12.5, 12.5], [-62.5, 12.5, 12.5], [-47.5, 12.5, 12.5],
                        [-32.5, 12.5, 12.5], [-17.5, 12.5, 12.5]])

    cable.addObject('CableConstraint', name="aCableActuator",
                    indices=list(range(0, 14)),
                    pullPoint=[0.0, 12.5, 2.5])

    cable.addObject('BarycentricMapping')

    # Tích hợp bộ điều khiển
    cable.addObject(AutoFlexController(name="AutoController", actuator=cable.aCableActuator))

    # --- ĐẠI LƯỢNG ĐẦU RA (Output/Visualization) ---
    finger.addChild(VisualModel(visualMeshPath=path + "finger.stl", color=[0.0, 0.7, 0.7, 1.0]))
    finger.VisualModel.addObject('BarycentricMapping', name='mapping')
    
    # [TỰ ĐỘNG LƯU KẾT QUẢ VÀO THƯ MỤC results/]
    finger.addObject('VTKExporter', filename=result_path + 'finger_deformation', edges=True, triangles=True, exportAtBegin=True, exportEveryNumberOfSteps=10)

    return rootNode