bl_info = {
    "name": "COM Locator",
    "author": "Dahus",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > COM Locator",
    "description": "Center of Mass locator with support plane",
    "category": "Animation",
}


import bpy
from mathutils import Vector
from bpy.app.handlers import persistent
from bpy.props import (
    StringProperty,
    FloatProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import PropertyGroup, Panel, Operator


COM_COLLECTION_NAME = "COM Locator"


# ============ PROPERTY GROUPS ============

class BoneItem(PropertyGroup):
    """Элемент списка для хранения имени кости"""
    name: StringProperty(
        name="Bone Name",
        description="Имя кости"
    )
    weight: FloatProperty(
        name="Weight",
        description="Вес кости для расчета центра масс",
        default=1.0,
        min=0.0,
        max=100.0
    )


class COMLocatorSettings(PropertyGroup):
    """Настройки для COM локатора"""
    
    armature_name: PointerProperty(
        name="Armature",
        description="Арматура для отслеживания",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )
    
    locator_name: StringProperty(
        name="Locator Name",
        description="Имя локатора центра масс",
        default="COM_Locator"
    )
    
    support_plane_name: StringProperty(
        name="Support Plane Name",
        description="Имя плоскости опоры",
        default="COM_Support_Plane"
    )
    
    # Списки костей
    tracked_bones: CollectionProperty(type=BoneItem)
    tracked_bones_index: IntProperty()
    
    support_bones: CollectionProperty(type=BoneItem)
    support_bones_index: IntProperty()
    
    # Отступы для плоскости опоры
    support_margin_x_pos: FloatProperty(
        name="Margin X+",
        description="Отступ вправо (положительное направление X)",
        default=0.15,
        min=0.0,
        max=10.0
    )
    
    support_margin_x_neg: FloatProperty(
        name="Margin X-",
        description="Отступ влево (отрицательное направление X)",
        default=0.15,
        min=0.0,
        max=10.0
    )
    
    support_margin_y_pos: FloatProperty(
        name="Margin Y+",
        description="Отступ вперед (положительное направление Y)",
        default=0.15,
        min=0.0,
        max=10.0
    )
    
    support_margin_y_neg: FloatProperty(
        name="Margin Y-",
        description="Отступ назад (отрицательное направление Y)",
        default=0.15,
        min=0.0,
        max=10.0
    )
    
    support_offset_z: FloatProperty(
        name="Offset Z",
        description="Поднять/опустить плоскость относительно пола",
        default=0.0,
        min=-10.0,
        max=10.0
    )
    
    # Настройки
    default_tail_factor: FloatProperty(
        name="Tail Factor",
        description="0.0 = head, 1.0 = tail, 0.5 = середина",
        default=0.5,
        min=0.0,
        max=1.0
    )


# ============ OPERATORS ============

class COM_OT_AddTrackedBone(Operator):
    """Добавить кость для отслеживания центра масс"""
    bl_idname = "com.add_tracked_bone"
    bl_label = "Add Tracked Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    bone_name: StringProperty(name="Bone")
    
    def execute(self, context):
        settings = context.scene.com_locator_settings
        
        if not self.bone_name:
            self.report({'WARNING'}, "Выберите кость")
            return {'CANCELLED'}
        
        # Проверяем, не добавлена ли уже эта кость
        if any(b.name == self.bone_name for b in settings.tracked_bones):
            self.report({'WARNING'}, f"Кость '{self.bone_name}' уже добавлена")
            return {'CANCELLED'}
        
        item = settings.tracked_bones.add()
        item.name = self.bone_name
        settings.tracked_bones_index = len(settings.tracked_bones) - 1
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        settings = context.scene.com_locator_settings
        
        if not settings.armature_name:
            self.report({'WARNING'}, "Сначала выберите арматуру")
            return {'CANCELLED'}
        
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.com_locator_settings
        
        if settings.armature_name and settings.armature_name.type == 'ARMATURE':
            layout.prop_search(self, "bone_name", settings.armature_name.data, "bones")
        else:
            layout.label(text="Арматура не выбрана")


class COM_OT_RemoveTrackedBone(Operator):
    """Удалить кость из отслеживания"""
    bl_idname = "com.remove_tracked_bone"
    bl_label = "Remove Tracked Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.com_locator_settings
        
        if settings.tracked_bones_index >= 0 and settings.tracked_bones_index < len(settings.tracked_bones):
            settings.tracked_bones.remove(settings.tracked_bones_index)
            settings.tracked_bones_index = min(settings.tracked_bones_index, len(settings.tracked_bones) - 1)
        
        return {'FINISHED'}


class COM_OT_AddSupportBone(Operator):
    """Добавить кость для плоскости опоры"""
    bl_idname = "com.add_support_bone"
    bl_label = "Add Support Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    bone_name: StringProperty(name="Bone")
    
    def execute(self, context):
        settings = context.scene.com_locator_settings
        
        if not self.bone_name:
            self.report({'WARNING'}, "Выберите кость")
            return {'CANCELLED'}
        
        # Проверяем, не добавлена ли уже эта кость
        if any(b.name == self.bone_name for b in settings.support_bones):
            self.report({'WARNING'}, f"Кость '{self.bone_name}' уже добавлена")
            return {'CANCELLED'}
        
        item = settings.support_bones.add()
        item.name = self.bone_name
        settings.support_bones_index = len(settings.support_bones) - 1
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        settings = context.scene.com_locator_settings
        
        if not settings.armature_name:
            self.report({'WARNING'}, "Сначала выберите арматуру")
            return {'CANCELLED'}
        
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.com_locator_settings
        
        if settings.armature_name and settings.armature_name.type == 'ARMATURE':
            layout.prop_search(self, "bone_name", settings.armature_name.data, "bones")
        else:
            layout.label(text="Арматура не выбрана")


class COM_OT_RemoveSupportBone(Operator):
    """Удалить кость из плоскости опоры"""
    bl_idname = "com.remove_support_bone"
    bl_label = "Remove Support Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.com_locator_settings
        
        if settings.support_bones_index >= 0 and settings.support_bones_index < len(settings.support_bones):
            settings.support_bones.remove(settings.support_bones_index)
            settings.support_bones_index = min(settings.support_bones_index, len(settings.support_bones) - 1)
        
        return {'FINISHED'}


class COM_OT_SetupLocator(Operator):
    """Создать и настроить COM локатор"""
    bl_idname = "com.setup_locator"
    bl_label = "Setup COM Locator"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.com_locator_settings
        
        if not settings.armature_name:
            self.report({'ERROR'}, "Выберите арматуру")
            return {'CANCELLED'}
        
        # УБРАЛИ проверку на support_bones
        
        result = setup_com_locator(context)
        
        if result:
            self.report({'INFO'}, "COM локатор успешно создан")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Ошибка при создании локатора")
            return {'CANCELLED'}


class COM_OT_RemoveLocator(Operator):
    """Удалить COM локатор и плоскость опоры"""
    bl_idname = "com.remove_locator"
    bl_label = "Remove COM Locator"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.com_locator_settings
        
        # Удаляем ОБА хендлера
        if update_com_locator in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(update_com_locator)
        
        if update_com_locator_on_frame_change in bpy.app.handlers.frame_change_post:
            bpy.app.handlers.frame_change_post.remove(update_com_locator_on_frame_change)
        
        # Удаляем локатор
        if settings.locator_name in bpy.data.objects:
            locator = bpy.data.objects[settings.locator_name]
            bpy.data.objects.remove(locator, do_unlink=True)
        
        # Удаляем плоскость опоры
        if settings.support_plane_name in bpy.data.objects:
            plane = bpy.data.objects[settings.support_plane_name]
            mesh = plane.data
            
            bpy.data.objects.remove(plane, do_unlink=True)
            
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        
        # Проверяем коллекцию и удаляем её, если пустая
        if COM_COLLECTION_NAME in bpy.data.collections:
            com_collection = bpy.data.collections[COM_COLLECTION_NAME]
            
            # Если коллекция пустая - удаляем её
            if len(com_collection.objects) == 0:
                bpy.data.collections.remove(com_collection)
                self.report({'INFO'}, "COM локатор и коллекция удалены")
            else:
                self.report({'INFO'}, "COM локатор удален (коллекция содержит другие объекты)")
        else:
            self.report({'INFO'}, "COM локатор удален")
        
        return {'FINISHED'}

# ============ PANEL ============

class COM_PT_MainPanel(Panel):
    """Главная панель для настройки COM локатора"""
    bl_label = "COM Locator"
    bl_idname = "COM_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'COM Locator'
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.com_locator_settings
        
        # Основные настройки
        box = layout.box()
        box.label(text="Basic Settings:", icon='SETTINGS')
        box.prop(settings, "armature_name")
        box.prop(settings, "locator_name")
        box.prop(settings, "support_plane_name")
        
        layout.separator()
        
        # Tracked Bones
        box = layout.box()
        box.label(text="Tracked Bones (Center of Mass):", icon='BONE_DATA')
        
        if len(settings.tracked_bones) == 0:
            box.label(text="Пусто = все кости арматуры", icon='INFO')
        
        row = box.row()
        row.template_list(
            "COM_UL_BoneList", "tracked_bones",
            settings, "tracked_bones",
            settings, "tracked_bones_index",
            rows=3
        )
        
        col = row.column(align=True)
        col.operator("com.add_tracked_bone", icon='ADD', text="")
        col.operator("com.remove_tracked_bone", icon='REMOVE', text="")
        
        layout.separator()
        
        # Support Bones
        box = layout.box()
        box.label(text="Support Bones (Support Plane):", icon='BONE_DATA')

        if len(settings.support_bones) == 0:
            box.label(text="Empty = no plane is created", icon='INFO')  # Изменили текст

        row = box.row()
        row.template_list(
            "COM_UL_BoneList", "support_bones",
            settings, "support_bones",
            settings, "support_bones_index",
            rows=3
        )
        
        col = row.column(align=True)
        col.operator("com.add_support_bone", icon='ADD', text="")
        col.operator("com.remove_support_bone", icon='REMOVE', text="")
        
        layout.separator()
        
        # Offsets
        box = layout.box()
        box.label(text="Support Plane Margins:", icon='EMPTY_ARROWS')
        
        # X margins
        row = box.row(align=True)
        row.prop(settings, "support_margin_x_neg")
        row.prop(settings, "support_margin_x_pos")
        
        # Y margins
        row = box.row(align=True)
        row.prop(settings, "support_margin_y_neg")
        row.prop(settings, "support_margin_y_pos")
        
        # Z offset
        box.prop(settings, "support_offset_z")
        
        layout.separator()
        
        # Advanced Settings
        box = layout.box()
        box.label(text="Advanced Settings:", icon='MODIFIER')
        box.prop(settings, "default_tail_factor")
        
        layout.separator()
        
        # Actions
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("com.setup_locator", icon='PLAY')
        row.operator("com.remove_locator", icon='CANCEL')


class COM_UL_BoneList(bpy.types.UIList):
    """UI List для отображения списка костей"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        settings = context.scene.com_locator_settings
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.label(text=item.name, icon='BONE_DATA')
            
            # Показываем вес только для tracked_bones
            if active_propname == "tracked_bones_index":
                row.prop(item, "weight", text="", emboss=True)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='BONE_DATA')


# ============ CORE FUNCTIONS ============

def get_bone_world_position(armature_obj, bone_name, tail_factor=0.5):
    if bone_name not in armature_obj.pose.bones:
        return None
    
    pose_bone = armature_obj.pose.bones[bone_name]
    bone_matrix = armature_obj.matrix_world @ pose_bone.matrix
    edit_bone = armature_obj.data.bones[bone_name]
    
    head_local = Vector((0, 0, 0))
    tail_local = Vector((0, edit_bone.length, 0))
    point_local = head_local.lerp(tail_local, tail_factor)
    
    return bone_matrix @ point_local


def calculate_center_of_mass(armature_obj, tracked_bones, default_tail_factor):
    total_weight = 0.0
    weighted_position = Vector((0, 0, 0))
    
    # Если список пустой - используем все кости с весом 1.0
    if len(tracked_bones) == 0:
        bones_to_track = [(b.name, 1.0) for b in armature_obj.data.bones]
    else:
        bones_to_track = [(b.name, b.weight) for b in tracked_bones]
    
    for bone_name, weight in bones_to_track:
        pos = get_bone_world_position(armature_obj, bone_name, default_tail_factor)
        if pos:
            weighted_position += pos * weight
            total_weight += weight
    
    if total_weight > 0:
        return weighted_position / total_weight
    return Vector((0, 0, 0))


def calculate_support_polygon(armature_obj, support_bones, margin_x_pos, margin_x_neg, margin_y_pos, margin_y_neg, offset_z):
    """Вычисляет центр и размер плоскости опоры на основе костей стоп."""
    if len(support_bones) == 0:
        return None, None, None
    
    positions = []
    for bone_item in support_bones:
        pos = get_bone_world_position(armature_obj, bone_item.name, 0.0)
        if pos:
            positions.append(pos)
    
    if len(positions) < 2:
        return None, None, None
    
    # Вычисляем границы
    min_x = min(p.x for p in positions)
    max_x = max(p.x for p in positions)
    min_y = min(p.y for p in positions)
    max_y = max(p.y for p in positions)
    
    # Применяем отступы к каждой стороне
    min_x -= margin_x_neg
    max_x += margin_x_pos
    min_y -= margin_y_neg
    max_y += margin_y_pos
    
    # Вычисляем центр с учетом отступов
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    
    # Размеры
    size_x = max_x - min_x
    size_y = max_y - min_y
    
    # Берем минимальную Z координату (пол) + смещение
    z_floor = min(p.z for p in positions) + offset_z
    
    center = Vector((center_x, center_y, z_floor))
    
    return center, size_x, size_y


def create_support_plane(plane_name, armature_obj):
    """Создает или обновляет плоскость опоры."""
    if plane_name in bpy.data.objects:
        plane = bpy.data.objects[plane_name]
        if plane.data:
            bpy.data.meshes.remove(plane.data)
    
    mesh = bpy.data.meshes.new(plane_name + "_mesh")
    plane = bpy.data.objects.new(plane_name, mesh)
    
    # Добавляем в COM коллекцию вместо текущей
    com_collection = get_or_create_com_collection()
    com_collection.objects.link(plane)
    
    plane.show_in_front = True
    plane.display_type = 'SOLID'
    
    # Добавляем constraint Child Of к арматуре
    if armature_obj:
        constraint = plane.constraints.new(type='CHILD_OF')
        constraint.target = armature_obj
        constraint.name = "Follow_Armature"
        
        # Устанавливаем inverse matrix вручную
        constraint.inverse_matrix = armature_obj.matrix_world.inverted()
    
    if not plane.data.materials:
        mat = bpy.data.materials.new(name="COM_Support_Material")
        mat.use_nodes = True
        mat.blend_method = 'BLEND'
        
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.0, 0.8, 0.2, 1.0)
            bsdf.inputs['Alpha'].default_value = 0.3
        
        plane.data.materials.append(mat)
    
    return plane

def update_support_plane_geometry(plane, center, size_x, size_y, armature_obj):
    """Обновляет геометрию плоскости."""
    mesh = plane.data
    mesh.clear_geometry()
    
    half_x = size_x / 2
    half_y = size_y / 2
    
    verts = [
        (-half_x, -half_y, 0),
        (half_x, -half_y, 0),
        (half_x, half_y, 0),
        (-half_x, half_y, 0)
    ]
    
    faces = [(0, 1, 2, 3)]
    
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    
    # Преобразуем мировые координаты в локальные координаты арматуры
    if armature_obj:
        local_pos = armature_obj.matrix_world.inverted() @ center
        plane.location = local_pos
    else:
        plane.location = center


@persistent
def update_com_locator(scene):
    try:
        settings = bpy.context.scene.com_locator_settings
        
        if not settings.armature_name:
            return
        
        armature = settings.armature_name
        locator = bpy.data.objects.get(settings.locator_name)
        plane = bpy.data.objects.get(settings.support_plane_name)
        
        # Обновляем локатор центра масс
        if locator:
            com_position = calculate_center_of_mass(
                armature,
                settings.tracked_bones,
                settings.default_tail_factor
            )
            
            # Проверяем, есть ли плоскость опоры
            plane_z = None
            if len(settings.support_bones) > 0 and plane:
                center, size_x, size_y = calculate_support_polygon(
                    armature,
                    settings.support_bones,
                    settings.support_margin_x_pos,
                    settings.support_margin_x_neg,
                    settings.support_margin_y_pos,
                    settings.support_margin_y_neg,
                    settings.support_offset_z
                )
                if center and size_x and size_y:
                    update_support_plane_geometry(plane, center, size_x, size_y, armature)
                    plane_z = center.z
            
            # Позиционируем локатор
            if plane_z is not None:
                # Есть плоскость - ставим стрелку так, чтобы кончик касался плоскости
                locator.location = Vector((com_position.x, com_position.y, plane_z + 1.0))
            else:
                # Нет плоскости - просто ставим локатор в центр масс
                locator.location = com_position
    except:
        pass
    
@persistent
def update_com_locator_on_frame_change(scene):
    """Обновление при смене кадра (для воспроизведения анимации)"""
    update_com_locator(scene)


def create_com_locator(locator_name):
    if locator_name in bpy.data.objects:
        return bpy.data.objects[locator_name]
    
    current_mode = bpy.context.mode
    if current_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.object.select_all(action='DESELECT')
    
    # Стрелка мешем: стержень + конус на конце
    verts = [
        # Стержень
        (-0.02, -0.02,  0.0),  # 0
        ( 0.02, -0.02,  0.0),  # 1
        ( 0.02,  0.02,  0.0),  # 2
        (-0.02,  0.02,  0.0),  # 3
        (-0.02, -0.02, -0.7),  # 4
        ( 0.02, -0.02, -0.7),  # 5
        ( 0.02,  0.02, -0.7),  # 6
        (-0.02,  0.02, -0.7),  # 7
        # Основание конуса
        (-0.07, -0.07, -0.7),  # 8
        ( 0.07, -0.07, -0.7),  # 9
        ( 0.07,  0.07, -0.7),  # 10
        (-0.07,  0.07, -0.7),  # 11
        # Кончик вниз
        (0.0, 0.0, -1.0),      # 12
    ]
    faces = [
        # Стержень
        (0,1,2,3),  # низ
        (0,1,5,4),
        (1,2,6,5),
        (2,3,7,6),
        (3,0,4,7),
        # Основание конуса
        (8,9,10,11),
        # Грани конуса
        (8,9,12),
        (9,10,12),
        (10,11,12),
        (11,8,12),
    ]
    
    mesh = bpy.data.meshes.new(locator_name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    
    locator = bpy.data.objects.new(locator_name, mesh)
    
    # Оранжевый материал
    mat = bpy.data.materials.new(name="COM_Locator_Material")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (1.0, 0.4, 0.0, 1.0)
        bsdf.inputs['Emission Color'].default_value = (1.0, 0.4, 0.0, 1.0)
        bsdf.inputs['Emission Strength'].default_value = 3.0
    mesh.materials.append(mat)
    
    locator.show_in_front = True
    locator.show_name = False
    
    com_collection = get_or_create_com_collection()
    com_collection.objects.link(locator)
    
    return locator

def setup_com_locator(context):
    settings = context.scene.com_locator_settings
    
    if not settings.armature_name or settings.armature_name.type != 'ARMATURE':
        return False
    
    create_com_locator(settings.locator_name)
    
    if len(settings.support_bones) > 0:
        create_support_plane(settings.support_plane_name, settings.armature_name)
    
    # Удаляем старые хендлеры если есть
    if update_com_locator in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_com_locator)
    
    if update_com_locator_on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(update_com_locator_on_frame_change)
    
    # Добавляем оба хендлера
    bpy.app.handlers.depsgraph_update_post.append(update_com_locator)
    bpy.app.handlers.frame_change_post.append(update_com_locator_on_frame_change)
    
    update_com_locator(context.scene)
    
    return True

def get_or_create_com_collection():
    """Получить или создать коллекцию для COM объектов"""
    if COM_COLLECTION_NAME in bpy.data.collections:
        return bpy.data.collections[COM_COLLECTION_NAME]
    
    # Создаем новую коллекцию
    collection = bpy.data.collections.new(COM_COLLECTION_NAME)
    
    # Добавляем в главную сцену
    bpy.context.scene.collection.children.link(collection)
    
    return collection


# ============ REGISTRATION ============

classes = (
    BoneItem,
    COMLocatorSettings,
    COM_OT_AddTrackedBone,
    COM_OT_RemoveTrackedBone,
    COM_OT_AddSupportBone,
    COM_OT_RemoveSupportBone,
    COM_OT_SetupLocator,
    COM_OT_RemoveLocator,
    COM_UL_BoneList,
    COM_PT_MainPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.com_locator_settings = PointerProperty(type=COMLocatorSettings)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.com_locator_settings
    
    # Удаляем ОБА хендлера при выгрузке аддона
    if update_com_locator in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_com_locator)
    
    if update_com_locator_on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(update_com_locator_on_frame_change)

if __name__ == "__main__":
    register()
