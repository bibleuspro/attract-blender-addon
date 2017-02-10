





















































































































             blender_id_text = "This add-on requires Blender ID" 


             blender_id_help = ("Make sure that the Blender ID add-on is " 


                 "installed and activated") 


-        elif blender_id_profile.unique_id == 0: 


+        elif blender_id_profile.unique_id == "": 


             blender_id_icon = 'ERROR' 


             blender_id_text = "You are logged out." 


             blender_id_help = ("To login, " 
 
@@ -136,7 +136,7 @@ def draw(self, context):


         # options for attract 


         sub = layout.column() 


         sub.enabled = (blender_id_profile != None 


-            and blender_id_profile.unique_id != 0) 


+            and blender_id_profile.unique_id != "") 


         sub.prop(self, "attract_server") 


         sub.operator("attract.credentials_update") 
