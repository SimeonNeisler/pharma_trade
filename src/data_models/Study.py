class Study:
    def __init__(self, nctid, title, phase, pcd, primary_sponsor, conditions):
        self.nctid = nctid
        self.title = title
        self.phase = phase
        self.pcd = pcd
        self.primary_sponsor = primary_sponsor
        self.conditions = conditions

    def __repr__(self):
        return f"Study(study_id={self.nctid}, title={self.title}, phase={self.phase}, pcd_str={self.pcd.strftime('%Y-%m-%d') if self.pcd else None}, primary_sponsor={self.primary_sponsor}, conditions={self.conditions})"
    
