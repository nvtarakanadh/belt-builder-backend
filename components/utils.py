COMPONENT_PLACEMENT_RULES = {
    "Base": {"mountable_sides": ["top"], "compatible": ["Motor", "Roller"], "supported_orientations": ["fixed"]},
    "Motor": {"mountable_sides": ["bottom"], "compatible": ["Base"], "supported_orientations": ["fixed"]},
    "Roller": {"mountable_sides": ["bottom"], "compatible": ["Base"], "supported_orientations": ["fixed"]},
    "Belt": {"mountable_sides": ["top"], "compatible": ["Roller"], "supported_orientations": ["fixed"]},
    "Frame": {"mountable_sides": ["top", "bottom"], "compatible": ["Base"], "supported_orientations": ["fixed"]},
}

def default_snap_positions_for_side(side: str):
    if side == 'bottom':
        return [0, 0, -5]
    if side == 'top':
        return [0, 5, 0]
    return [0, 0, 0]


