from dataclasses import dataclass


@dataclass
class Workbenches:
    Arch: str = "BIMWorkbench"
    PD: str = "PartDesignWorkbench"
    FEM: str = "FemWorkbench"
    SheetMetal: str = "SMWorkbench"
    Asm4: str = "Assembly4Workbench"
    a2p: str = "A2plusWorkbench"
    Materials: str = "MaterialWorkbench"
    FCGear: str = "GearWorkbench"
    FreeCAD: str = "Std"


DEFAULT_WORKBENCH = "PartDesignWorkbench"
PARAM_PATH = "User parameter:BaseApp/OverlayToolbar"
