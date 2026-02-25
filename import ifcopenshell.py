import ifcopenshell

ifc_model = ifcopenshell.open(r"C:\Users\burka\github-classroom\iaac-maai\intro-to-ifc-seidburka\assets\duplex.ifc")
print("Model loaded!")

all_windows = ifc_model.by_type("IfcWindow")
print(f"Found {len(all_windows)} windows")

w = all_windows[0]
print(w.Name, w.OverallWidth, w.OverallHeight)