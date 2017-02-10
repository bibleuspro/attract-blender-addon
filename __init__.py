# ##### BEGIN GPL LICENSE BLOCK #####

#

#  This program is free software; you can redistribute it and/or

#  modify it under the terms of the GNU General Public License

#  as published by the Free Software Foundation; either version 2

#  of the License, or (at your option) any later version.

#

#  This program is distributed in the hope that it will be useful,

#  but WITHOUT ANY WARRANTY; without even the implied warranty of

#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the

#  GNU General Public License for more details.

#

#  You should have received a copy of the GNU General Public License

#  along with this program; if not, write to the Free Software Foundation,

#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

#

# ##### END GPL LICENSE BLOCK #####



# <pep8-80 compliant>



bl_info = {

    "name": "Attract",

    "author": "Francesco Siddi, Inês Almeida, Antony Riakiotakis",

    "version": (0, 2, 0),

    "blender": (2, 76, 0),

    "location": "Video Sequence Editor",

    "description":

        "Blender integration with the Attract task tracking service"

        ". *requires the Blender ID add-on",

    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"

                "Scripts/Workflow/Attract",

    "category": "Workflow",

    "support": "TESTING"

}



if "bpy" in locals():

    import importlib

    importlib.reload(draw)

else:

    from . import draw



import bpy

import os

from .attractsdk.api import Api

from .attractsdk.nodes import Node

from .attractsdk.nodes import NodeType

from .attractsdk import utils

from .attractsdk.exceptions import ResourceNotFound



from bpy.props import StringProperty

from bpy.types import Operator

from bpy.types import Panel

from bpy.types import AddonPreferences





def active_strip(context):

    try:

        return context.scene.sequence_editor.active_strip

    except AttributeError:

        return None





class SystemUtility():

    def __new__(cls, *args, **kwargs):

        raise TypeError("Base class may not be instantiated")



    @staticmethod

    def update_attract_api(endpoint="http://attract:5000"):

        blender_id_profile = getattr(

            context.window_manager,

            "blender_id_active_profile",

            None

        )

        if blender_id_profile:

            Api.Default(

                endpoint=endpoint,

                username=None,

                password=None,

                token=blender_id_profile.token

            )

            return True

            # Alternatively we can provide a new instance of the Api

            # class for each request

        else:

            return None



    @staticmethod

    def remove_atc_props(strip):

        """Resets the attract custom properties assigned to a VSE strip"""

        strip.atc_cut_in = 0

        strip.atc_cut_out = 0

        strip.atc_name = ""

        strip.atc_description = ""

        strip.atc_object_id = ""

        strip.atc_is_synced = False





class AttractPreferences(AddonPreferences):

    bl_idname = __name__



    attract_server = bpy.props.StringProperty(

        name="Attract Server",

        description="Address and port of the Attract server",

        default="http://localhost:5000"

    )



    def draw(self, context):

        layout = self.layout

        sub = layout.column()



        # get active profile information from the blender id add-on

        blender_id_profile = getattr(

            context.window_manager,

            "blender_id_active_profile",

            None

        )

        if blender_id_profile is None:

            blender_id_icon = 'ERROR'

            blender_id_text = "This add-on requires Blender ID"

            blender_id_help = ("Make sure that the Blender ID add-on is "

                "installed and activated")

        elif blender_id_profile.unique_id == "":

            blender_id_icon = 'ERROR'

            blender_id_text = "You are logged out."

            blender_id_help = ("To login, "

                "go to the Blender ID add-on preferences.")

        else:

            blender_id_icon = 'WORLD_DATA'

            blender_id_text = format("You are logged in as %s."

                % blender_id_profile.unique_id)

            blender_id_help = ("To logout or change profile, "

                "go to the Blender ID add-on preferences.")

        sub.label(text=blender_id_text, icon=blender_id_icon)

        sub.label(text="* " + blender_id_help)



        # options for attract

        sub = layout.column()

        sub.enabled = (blender_id_profile != None

            and blender_id_profile.unique_id != "")

        sub.prop(self, "attract_server")

        sub.operator("attract.credentials_update")





class ToolsPanel(Panel):

    bl_label = "Attract"

    bl_space_type = "SEQUENCE_EDITOR"

    bl_region_type = "UI"



    def draw_header(self, context):

        strip = active_strip(context)

        if strip and strip.atc_object_id:

            self.layout.prop(strip, "atc_is_synced", text="")



    def draw(self, context):

        strip = active_strip(context)

        layout = self.layout

        if strip and strip.atc_object_id and strip.type in ['MOVIE', 'IMAGE']:

            layout.prop(strip, "atc_name", text="Name")

            layout.prop(strip, "atc_description", text="Description")

            layout.prop(strip, "atc_notes", text="Notes")

            layout.prop(strip, "atc_status", text="Status")

            layout.prop(strip, "atc_cut_in", text="Cut in")

            # layout.prop(strip, "atc_cut_out", text="Cut out")



            if strip.atc_is_synced:

                layout.operator("attract.shot_submit_update")

                layout.operator("attract.shot_delete")

                layout.operator("attract.strip_unlink")



        elif strip and strip.type in ['MOVIE', 'IMAGE']:

            layout.operator("attract.shot_submit_new")

            layout.operator("attract.shot_relink")

        else:

            layout.label(text="Select a movie strip")

        layout.operator("attract.shots_order_update")





class AttractCredentialsUpdate(Operator):

    """

    """

    bl_idname = "attract.credentials_update"

    bl_label = "Update credentials"



    def execute(self, context):

        blender_id_profile = getattr(

            context.window_manager,

            "blender_id_active_profile",

            None

        )

        if blender_id_profile:

            preferences = context.user_preferences.addons[__name__].preferences

            SystemUtility.update_attract_api(endpoint=preferences.attract_server)

            try:

                Node.all()

            except Exception as e:

                print(e)

                self.report({'ERROR'}, "Failed connection to {0}".format(

                    preferences.attract_server))

                return{'FINISHED'}



            self.report({'INFO'}, "Updated credentials for {0}".format(

                preferences.attract_server))

        else:

            self.report({'ERROR'}, "No profile active found")



        return{'FINISHED'}





class AttractShotSubmitNew(Operator):

    bl_idname = "attract.shot_submit_new"

    bl_label = "Submit to Attract"

    def execute(self, context):

        strip = active_strip(context)

        if not strip.atc_object_id or strip.atc_object_id == "":

            # Filter the NodeType collection, but it's still a list

            node_type_list = NodeType.all({'where': "name=='shot'"})

            # Get the 'shot' node type

            node_type = node_type_list['_items'][0]

            # Define the shot properties

            prop = {}

            prop['name'] = strip.name

            prop['description'] = ""

            prop['properties'] = {}

            prop['properties']['status'] = 'on_hold'

            prop['properties']['notes'] = ""

            prop['properties']['cut_in'] = strip.frame_offset_start

            prop['properties']['cut_out'] = strip.frame_offset_start + strip.frame_final_duration

            prop['order'] = 0

            prop['node_type'] = node_type['_id']



            blender_id_profile = getattr(

                context.window_manager,

                "blender_id_active_profile",

                None

            )

            token = blender_id_profile.token

            params = {'where': '{"token": "%s"}' % (token)}

            url = utils.join_url_params("tokens", params)

            token = Api.Default().get(url)

            # Add the user_id to the properties

            prop['user'] = token['_items'][0]['user']

            # Create a Node item with the attract API

            node = Node(prop)

            post = node.create()



            # Populate the strip with the freshly generated ObjectID and info

            if post:

                strip.atc_object_id = node['_id']

                strip.atc_is_synced = True

                strip.atc_name = node['name']

                strip.atc_cut_in = node['properties']['cut_in']

                strip.atc_cut_out = node['properties']['cut_out']



        return{'FINISHED'}





class AttractShotRelink(Operator):

    bl_idname = "attract.shot_relink"

    bl_label = "Relink to Attract"

    strip_atc_object_id = bpy.props.StringProperty()



    def execute(self, context):

        strip = active_strip(context)

        try:

            node = Node.find(self.strip_atc_object_id)

        except ResourceNotFound:

            self.report({'ERROR'}, "No shot found on the server")



        strip.atc_object_id = self.strip_atc_object_id

        strip.atc_is_synced = True

        strip.atc_name = node.name

        strip.atc_cut_in = node.properties.cut_in

        strip.atc_cut_out = node.properties.cut_out

        strip.atc_description = node.description

        self.report({'INFO'}, "Shot {0} relinked".format(node.name))

        return{'FINISHED'}



    def invoke(self, context, event):

        return context.window_manager.invoke_props_dialog(self)



    def draw(self, context):

        layout = self.layout

        col = layout.column()

        col.prop(self, "strip_atc_object_id", text="Shot ID")





class AttractShotSubmitUpdate(Operator):

    bl_idname = "attract.shot_submit_update"

    bl_label = "Update"

    bl_description = "Syncronizes local and remote changes"

    def execute(self, context):

        strip = active_strip(context)

        # Update cut_in and cut_out properties on the strip

        # strip.atc_cut_in = strip.frame_offset_start

        # strip.atc_cut_out = strip.frame_offset_start + strip.frame_final_duration

        # print("Query Attract server with {0}".format(strip.atc_object_id))

        strip.atc_cut_out = strip.atc_cut_in + strip.frame_final_duration - 1

        node = Node.find(strip.atc_object_id)

        node.name = strip.atc_name

        node.description = strip.atc_description

        node.properties.cut_in = strip.atc_cut_in

        node.properties.cut_out = strip.atc_cut_out

        node.update()

        return{'FINISHED'}





class AttractShotDelete(Operator):

    bl_idname = "attract.shot_delete"

    bl_label = "Delete"

    bl_description = "Remove from Attract"

    def execute(self, context):

        strip = active_strip(context)

        node = Node.find(strip.atc_object_id)

        if node.delete():

            SystemUtility.remove_atc_props(strip)

        return{'FINISHED'}





class AttractStripUnlink(Operator):

    bl_idname = "attract.strip_unlink"

    bl_label = "Unlink"

    bl_description = "Remove Attract props from the strip"

    def execute(self, context):

        strip = active_strip(context)

        SystemUtility.remove_atc_props(strip)

        return{'FINISHED'}





class AttractShotsOrderUpdate(Operator):

    bl_idname = "attract.shots_order_update"

    bl_label = "Update shots order"

    def execute(self, context):

        # Get all shot nodes from server, build dictionary using ObjectID

        # as indexes

        node_type_list = NodeType.all({'where': "name=='shot'"})

        node_type = node_type_list._items[0]



        shots = Node.all({

            'where': '{"node_type" : "%s"}' % (node_type._id),

            'max_results': 100})



        shots = shots._items



        # TODO (fsiddi) take into account pagination. Currently we do not do it

        # and it makes this dict useless.

        # We should use the pagination info from the node_type_list query and

        # keep querying until we have all the items.

        shots_dict = {}

        for shot in shots:

            shots_dict[shot._id] = shot



        # Build ordered list of strips from the edit

        strips_with_atc_object_id = []

        for strip in context.scene.sequence_editor.sequences_all:

            # If the shot has been added to Attract, and is in the list

            if strip.atc_object_id:

                strips_with_atc_object_id.append(strip)



        strips_with_atc_object_id.sort(

            key=lambda strip: strip.frame_start + strip.frame_offset_start)

        index = 1

        for strip in strips_with_atc_object_id:

            """

            # Currently we use the code below to force update all nodes.

            # Check that the shot is in the list of retrieved shots

            if strip.atc_order != index: #or shots_dict[strip.atc_object_id]['order'] != index:

                # If there is an update in the order, retrieve and update

                # the node, as well as the VSE strip

                # shot_node = Node.find(strip.atc_object_id)

                # shot_node.order = index

                # shot_node.update()

                # strip.atc_order = index

                print ("{0} > {1}".format(strip.atc_order, index))

            """

            # We get all nodes one by one. This is bad and stupid.

            try:

                shot_node = Node.find(strip.atc_object_id)

                # if shot_node.properties.order != index:

                shot_node.order = index

                shot_node.update()

                print('{0} - updating {1}'.format(shot_node.order, shot_node.name))

                strip.atc_order = index

                index += 1

            except ResourceNotFound:

                # Reset the attract properties for any shot not found on the server

                # print("Error: shot {0} not found".format(strip.atc_object_id))

                SystemUtility.remove_atc_props(strip)



        return{'FINISHED'}





def register():

    bpy.types.Sequence.atc_is_synced = bpy.props.BoolProperty(name="Is synced")

    bpy.types.Sequence.atc_object_id = bpy.props.StringProperty(name="Attract Object ID")

    bpy.types.Sequence.atc_name = bpy.props.StringProperty(name="Shot Name")

    bpy.types.Sequence.atc_description = bpy.props.StringProperty(name="Shot description")

    bpy.types.Sequence.atc_notes = bpy.props.StringProperty(name="Shot notes")

    bpy.types.Sequence.atc_cut_in = bpy.props.IntProperty(name="Cut in")

    bpy.types.Sequence.atc_cut_out = bpy.props.IntProperty(name="Cut out")

    bpy.types.Sequence.atc_status = bpy.props.EnumProperty(

        items = [

            ('on_hold', 'On hold', 'The shot is on hold'),

            ('todo', 'Todo', 'Waiting'),

            ('in_progress', 'In progress', 'The show has been assigned')],

        name="Status")

    bpy.types.Sequence.atc_order = bpy.props.IntProperty(name="Order")

    bpy.utils.register_module(__name__)

    draw.callback_enable()





def unregister():

    draw.callback_disable()

    del bpy.types.Sequence.atc_is_synced

    del bpy.types.Sequence.atc_object_id

    del bpy.types.Sequence.atc_name

    del bpy.types.Sequence.atc_description

    del bpy.types.Sequence.atc_notes

    del bpy.types.Sequence.atc_cut_in

    del bpy.types.Sequence.atc_cut_out

    del bpy.types.Sequence.atc_status

    del bpy.types.Sequence.atc_order

    bpy.utils.unregister_module(__name__)





if __name__ == "__main__":

    register()
