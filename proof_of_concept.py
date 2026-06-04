import matlab.engine

def list_sbiomodels(sbproj_path):
    eng = matlab.engine.start_matlab()
    
    # Load the project
    eng.eval(f"sbioloadproject('{sbproj_path}')", nargout=0)
    
    # Find all SimBiology.Model objects and get their .Name property
    eng.eval(
        "ws = whos; "
        "mask = arrayfun(@(s) strcmp(s.class, 'SimBiology.Model'), ws); "
        "modelVarNames = {ws(mask).name}; "
        "modelNames = cellfun(@(v) evalin('base', v).Name, modelVarNames, 'UniformOutput', false);",
        nargout=0
    )
    
    var_names = eng.eval("modelVarNames", nargout=1)
    model_names = eng.eval("modelNames", nargout=1)
    
    print("\nSimBiology models found:")
    for i, (var, name) in enumerate(zip(var_names, model_names)):
        print(f"  [{i}] workspace var: {var}  |  model name: {name}")
    
    # Prompt user to rename model
    print("\nEnter the index of the model you want to rename (or press Enter to skip): ", end="")
    choice = input().strip()
    
    if choice == "":
        print("No changes made to model name.")
    else:
        try:
            idx = int(choice)
            var = list(var_names)[idx]
            old_name = list(model_names)[idx]
            
            print(f"Enter new name for '{old_name}': ", end="")
            new_name = input().strip()
            
            if new_name == "":
                print("No changes made.")
            else:
                eng.eval(f"{var}.Name = '{new_name}';", nargout=0)
                print(f"Model renamed from '{old_name}' to '{new_name}'.")
        except (ValueError, IndexError):
            print("Invalid selection. No changes made.")

    # Pick which model to work with for compartments
    print("\nEnter the index of the model whose compartments you want to manage: ", end="")
    choice = input().strip()

    try:
        idx = int(choice)
        var = list(var_names)[idx]

        # Get all compartment names
        eng.eval(
            f"compObjs = {var}.Compartments; "
            "compNames = cellfun(@(c) c.Name, num2cell(compObjs), 'UniformOutput', false);",
            nargout=0
        )

        comp_names = eng.eval("compNames", nargout=1)

        if not comp_names:
            print("No compartments found in this model.")
        else:
            while True:
                print("\nCompartments found:")
                # Refresh compartment names each loop
                eng.eval(
                    f"compObjs = {var}.Compartments; "
                    "compNames = cellfun(@(c) c.Name, num2cell(compObjs), 'UniformOutput', false);",
                    nargout=0
                )
                comp_names = eng.eval("compNames", nargout=1)

                for i, name in enumerate(comp_names):
                    print(f"  [{i}] {name}")

                print("\nEnter the index of the compartment to rename (or press Enter to finish): ", end="")
                comp_choice = input().strip()

                if comp_choice == "":
                    print("Done renaming compartments.")
                    break

                try:
                    comp_idx = int(comp_choice) + 1  # MATLAB is 1-indexed
                    old_comp_name = list(comp_names)[comp_idx - 1]

                    print(f"Enter new name for compartment '{old_comp_name}': ", end="")
                    new_comp_name = input().strip()

                    if new_comp_name == "":
                        print("No changes made.")
                    else:
                        eng.eval(f"{var}.Compartments({comp_idx}).Name = '{new_comp_name}';", nargout=0)
                        print(f"Compartment renamed from '{old_comp_name}' to '{new_comp_name}'.")

                except (ValueError, IndexError):
                    print("Invalid selection. Try again.")

    except (ValueError, IndexError):
        print("Invalid selection. No compartment changes made.")

    # Save project
    print("\nSave changes to project? (y/n): ", end="")
    save_choice = input().strip().lower()
    if save_choice == "y":
        eng.eval(f"sbiosaveproject('{sbproj_path}');", nargout=0)
        print("Project saved.")
    else:
        print("Changes not saved.")

    eng.quit()

if __name__ == "__main__":
    sbproj_file = r"C:\Users\yojit\Documents\Yojith_Work\Yojith_Coding\SimbiologyMCP\project.sbproj"
    list_sbiomodels(sbproj_file)










    