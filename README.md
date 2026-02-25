[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/s5kpkRs_)
[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=22840899&assignment_repo_type=AssignmentRepo)
# IFC File Parsing and Building Code Compliance

A GitHub Classroom assignment to understand Industry Foundation Classes (IFC) and how to validate building designs against building codes.

## Overview

This assignment teaches you to:
1. Read and explore IFC building models
2. Extract spatial data (spaces, windows, doors)
3. Validate designs against the Catalan building code
4. Analyze fire safety and evacuation routes

The sample model is a duplex apartment (`assets/duplex.ifc`) that you'll use for all exercises.

## Getting Started

### Prerequisites

- Python 3.8+
- Jupyter Notebook
- IfcOpenShell (installed automatically)

### Setup

1. Clone this repository
2. Open `ifc-exercises.ipynb` in Jupyter
3. Run the setup cell to install dependencies
4. Follow along with the example and complete the exercises

## Assignment Structure

### Part 1: Example - Extract All Spaces ✓
Learn how to read an IFC file and extract all `IfcSpace` entities. This demonstrates basic IFC navigation and property extraction.

**What you'll learn:**
- Reading IFC files with IfcOpenShell
- Querying entity types
- Accessing spatial properties (area, volume, name)

### Part 2: Exercise 1 - Building Code Compliance
**Objective:** Write a function that checks if each room meets Catalan building code requirements.

**Requirements to validate:**
- Minimum room heights (2.3-2.6m depending on type)
- Minimum room areas (4-16 m² depending on type)
- Proper classification of space types

**Your deliverable:**
- Implement `check_space_compliance(spaces)` function
- Return a report of pass/fail for each space
- Identify why spaces fail if they do

**Reference:** [Catalan Building Code](https://notebooklm.google.com/notebook/216b245f-0fc1-4063-bdfd-d23b41360b0e)

### Part 3: Exercise 2 - Window Compliance
**Objective:** Find all windows and verify they meet natural light requirements.

**Requirements to validate:**
- Minimum window-to-floor ratio (≥12.5%)
- Minimum window dimensions (60cm × 100cm)
- Windows present in habitable spaces

**Your deliverable:**
- Implement `analyze_window_compliance(ifc_model, spaces)` function
- Report window-to-floor ratio per space
- Flag spaces that don't meet requirements

### Part 4: Bonus - Fire Safety Routes
**Objective (Advanced):** Analyze evacuation routes and validate fire safety requirements.

**Requirements to validate:**
- Maximum travel distance to exit (≤25m)
- Minimum corridor width (1.2m)
- Minimum door width (0.8m)
- No dead-end corridors > 10m

**Your deliverable:**
- Implement `analyze_evacuation_routes(ifc_model, spaces)` function
- Build a spatial connectivity graph
- Find the longest evacuation route
- Report compliance and safety issues

**Skills needed:**
- Graph algorithms (BFS/DFS)
- Spatial analysis
- Extracting geometry from IFC entities

## Hints for Solving Exercises

### General Tips
- Start with `ifc.by_type("IfcSpace")` to get all spaces
- Use `.Name` to get room names
- Check `.Quantities` for area/volume data
- Print entity attributes to explore structure: `print(dir(entity))`

### Exercise 1
- Infer space type from the name (e.g., "Master Bedroom" → "Bedroom")
- Height can be estimated from Z-coordinates or room properties
- Use keyword matching to classify spaces

### Exercise 2
- Get windows with `ifc.by_type("IfcWindow")`
- Find parent space by checking spatial relationships
- Calculate window area from dimensions or quantity data
- Divide window area by floor area to get ratio

### Bonus
- Model spaces as graph nodes
- Model doors as edges between spaces
- Use BFS to find paths from each space to exit
- Track the longest path found

## Useful Resources

### IFC Learning
- [IFC Knowledge Base](https://notebooklm.google.com/notebook/0925c2a1-519b-40a8-aca4-1e832d219f3c)
- [BuildingSmart IFC Standards](https://www.buildingsmart.org/standards/bsi-standards/industry-foundation-classes/)
- [IfcOpenShell Python Documentation](https://docs.ifcopenshell.org/ifcopenshell-python.html)

### Building Code
- [Catalan Building Code](https://notebooklm.google.com/notebook/216b245f-0fc1-4063-bdfd-d23b41360b0e)

## Submission

Submit your completed notebook with:
1. ✓ Example section working and showing all spaces
2. ✓ Exercise 1: `check_space_compliance()` function implemented
3. ✓ Exercise 2: `analyze_window_compliance()` function implemented
4. ✓ (Optional) Bonus: `analyze_evacuation_routes()` function implemented

Each function should:
- Handle errors gracefully
- Include docstrings explaining what it does
- Return structured results (dicts/lists)
- Print clear, readable output

### Code Quality Checklist
- [ ] Functions have clear docstrings
- [ ] Variables have meaningful names
- [ ] Code handles edge cases
- [ ] Output is formatted clearly
- [ ] No hardcoded assumptions

## Autograding (For Instructors)

This assignment includes automatic grading with GitHub Classroom. Detailed setup instructions are in [AUTOGRADING.md](AUTOGRADING.md).

**Quick setup:**
- Autograding tests are in `tests/test_autograder.py`
- Tests check function existence, return types, and basic functionality
- Configure in GitHub Classroom: ~5 minutes

Tests verify:
- ✅ Notebook structure and IFC file presence
- ✅ Exercise 1 function works and returns results
- ✅ Exercise 2 function works and returns results
- ✅ Code has proper documentation

Note: Autograding validates structure and basic functionality. Manual review is recommended for correctness of business logic and algorithm quality.

## Debugging Tips

### Check what's in the model
```python
# View all entity types and counts
for entity_type in sorted(set(e.is_a() for e in ifc.entities)):
    count = len(ifc.by_type(entity_type))
    print(f"{entity_type}: {count}")
```

### Explore a single entity
```python
space = ifc.by_type("IfcSpace")[0]
print(f"Name: {space.Name}")
print(f"Type: {space.is_a()}")
print(f"All attributes: {dir(space)}")
```

### Check relationships
```python
entity = ifc.by_type("IfcWindow")[0]
print(f"Placement: {entity.ObjectPlacement}")
print(f"Contained in: {entity.BoundedBy}")
```

## Questions?

Refer to the resources linked in the notebook or check the IfcOpenShell documentation. IFC is a complex standard—don't hesitate to explore the model structure to understand how data is organized.

Good luck! 🏗️
