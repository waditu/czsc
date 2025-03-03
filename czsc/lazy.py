import os
from types import ModuleType
from typing import Dict, List, Optional, Any

class LazyModule(ModuleType):
    """延迟加载模块，只有在访问属性时才导入实际模块"""

    def __init__(
            self, name,
            package=None,
            submodules=None,
            submod_attrs=None,
            old_obj=None):

        self.__name__ = name
        self.__package__ = package if package is not None else name
        self.__file__ = os.path.dirname(__file__)
        self.__path__ = [os.path.dirname(__file__)]
        self.__submodules__ = submodules if submodules is not None else []
        self.__submod_attrs__ = submod_attrs if submod_attrs is not None else {}
        self.__old_obj__ = old_obj

        # 延迟加载的缓存
        self.__module_cache__ = {}
        self.__imported__ = False

        # 存储外部包的直接导入项
        self.__external_imports__ = {
            "daily_performance": "rs_czsc",
            "top_drawdowns": "rs_czsc",
            "WeightBacktest": "rs_czsc",
        }

        # 立即导入外部依赖
        self._import_external()

    def _import_external(self):
        """立即导入外部包的对象"""
        for attr_name, module_name in self.__external_imports__.items():
            try:
                from importlib import import_module
                module = import_module(module_name)
                if hasattr(module, attr_name):
                    setattr(self, attr_name, getattr(module, attr_name))
            except (ImportError, AttributeError):
                # 如果导入失败，会在实际访问属性时再次尝试
                pass

    def __dir__(self):
        """返回模块包含的属性名称"""
        attrs = set()
        # 添加自定义模块属性
        if self.__old_obj__ is not None:
            attrs.update(dir(self.__old_obj__))

        # 添加子模块名称
        attrs.update(self.__submodules__)

        # 添加子模块中的属性
        for submod_attrs in self.__submod_attrs__.values():
            attrs.update(submod_attrs)

        # 添加外部导入
        attrs.update(self.__external_imports__.keys())

        # 添加版本信息等基本属性
        attrs.update(["__version__", "__author__", "__email__", "__date__"])

        return list(attrs)

    def __getattr__(self, name):
        """在访问属性时按需导入相应模块"""
        # 处理版本信息等基本属性
        if name in ["__version__", "__author__", "__email__", "__date__"]:
            return globals()[name]

        # 处理外部包导入
        if name in self.__external_imports__:
            try:
                from importlib import import_module
                module_name = self.__external_imports__[name]
                module = import_module(module_name)
                obj = getattr(module, name)
                setattr(self, name, obj)
                return obj
            except (ImportError, AttributeError) as e:
                raise AttributeError(f"Failed to import {name} from {module_name}: {e}")

        # 如果是子模块名称
        if name in self.__submodules__:
            try:
                from importlib import import_module
                submodule_name = f"{self.__name__}.{name}"
                if submodule_name not in self.__module_cache__:
                    self.__module_cache__[submodule_name] = import_module(submodule_name)
                return self.__module_cache__[submodule_name]
            except ImportError as e:
                raise AttributeError(f"Error loading submodule {name}: {e}")

        # 如果是子模块中的属性
        for mod_name, attrs in self.__submod_attrs__.items():
            if name in attrs:
                try:
                    from importlib import import_module
                    submodule_name = f"{self.__name__}.{mod_name}"
                    # 处理 utils.calendar 等多级子模块
                    if "." in mod_name:
                        submodule_name = f"{self.__name__}.{mod_name}"

                    if submodule_name not in self.__module_cache__:
                        self.__module_cache__[submodule_name] = import_module(submodule_name)
                    return getattr(self.__module_cache__[submodule_name], name)
                except (ImportError, AttributeError) as e:
                    raise AttributeError(f"Failed to import {name} from {submodule_name}: {e}")

        # 如果旧对象中有这个属性
        if self.__old_obj__ is not None and hasattr(self.__old_obj__, name):
            return getattr(self.__old_obj__, name)

        # 如果以上都没找到
        raise AttributeError(f"No attribute or submodule named '{name}' found in '{self.__name__}'")
