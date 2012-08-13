# coding=UTF-8
# ex:ts=4:sw=4:et=on

# Author: Mathijs Dumon
# This work is licensed under the Creative Commons Attribution-ShareAlike 3.0 Unported License. 
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/3.0/ or send
# a letter to Creative Commons, 444 Castro Street, Suite 900, Mountain View, California, 94041, USA.

import time
from warnings import warn

from math import sin, cos, pi, sqrt, exp

import gtk
from gtkmvc.model import Model
from gtkmvc.model import Signal, Observer

import numpy as np

from generic.metaclasses import pyxrd_object_pool
from generic.io import Storable, PyXRDDecoder
from generic.model_mixins import CSVMixin, ObjectListStoreChildMixin
from generic.models import ChildModel, PropIntel
from generic.treemodels import XYListStore

class AtomType(ChildModel, ObjectListStoreChildMixin, Storable, CSVMixin):
    """
        AtomTypes contain all physical & chemical information for one element 
        in a certain state (e.g. Fe3+ & Fe2+ are two different AtomTypes)
    """

    #MODEL INTEL:
    __index_column__ = 'name'
    __parent_alias__ = 'project'
    __model_intel__ = [ #TODO add labels
        PropIntel(name="atom_nr",      inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True, ctype=int,    refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="name",         inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True, ctype=str,    refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="charge",       inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True, ctype=float,  refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="weight",       inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True, ctype=float,  refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="debye",        inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True, ctype=float,  refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="par_c",        inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True, ctype=float,  refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="parameters_changed",inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True, ctype=float,  refinable=False, storable=False, observable=True,  has_widget=False),
    ] + [
        PropIntel(name="par_a%d" % i,  inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True, ctype=float,  refinable=False, storable=True,  observable=True,  has_widget=True) for i in [1,2,3,4,5]
    ] + [
        PropIntel(name="par_b%d" % i,  inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True, ctype=float,  refinable=False, storable=True,  observable=True,  has_widget=True) for i in [1,2,3,4,5]
    ]
    __csv_storables__ = [(prop.name, prop.name) for prop in __model_intel__ if prop.storable]

    
    #SIGNALS:
    parameters_changed = None
    
    #PROPERTIES:
    _name = ""
    def get_name_value(self): return self._name
    def set_name_value(self, value):
        self._name = value
        self.liststore_item_changed()
     
    atom_nr = 0
    weight = 0
    debye = 0
    charge = 0
    
    _a = None
    _b = None
    _c = 0
    
    @Model.getter("par_a*", "par_b*", "par_c")
    def get_atom_par(self, prop_name):
        name = prop_name[4]
        if name == "a":
            index = int(prop_name[-1:])-1
            return self._a[index]
        elif name == "b":
            index = int(prop_name[-1:])-1
            return self._b[index]
        elif name == "c":
            return self._c
        return None
        
    @Model.setter("par_a*", "par_b*", "par_c")
    def set_atom_par(self, prop_name, value):
        name = prop_name[4]
        if name == "a":
            index = int(prop_name[-1:])-1
            self._a[index] = value
            self.parameters_changed.emit()
        elif name == "b":
            index = int(prop_name[-1:])-1
            self._b[index] = value
            self.parameters_changed.emit()
        elif name == "c":
            self._c = value
            self.parameters_changed.emit()            

    # ------------------------------------------------------------
    #      Initialisation and other internals
    # ------------------------------------------------------------
    
    def __init__(self, name="", charge=0, debye=0, weight=0, atom_nr=0, par_c=0, 
            par_a1=0, par_a2=0, par_a3=0, par_a4=0, par_a5=0, 
            par_b1=0, par_b2=0, par_b3=0, par_b4=0, par_b5=0, 
            parent=None, **kwargs):
        ChildModel.__init__(self, parent=parent)
        Storable.__init__(self)
        self.parameters_changed = Signal()
               
        self.name = self.get_depr(("data_name",), kwargs, str(name) or self.name)
        self.atom_nr = self.get_depr(("data_atom_nr",), kwargs, int(atom_nr) or self.atom_nr)
        self.weight = self.get_depr(("data_weight",), kwargs, float(weight) or self.weight)
        self.debye = self.get_depr(("data_debye",), kwargs, float(debye) or self.debye)
        self.charge = self.get_depr(("data_charge",), kwargs, float(charge) or self.charge)
        
        self._c = self.get_depr(("data_par_c",), kwargs, float(par_c))

        self._a = []
        self._b = []
        for name in ["par_a1", "par_a2", "par_a3", "par_a4", "par_a5"]:
            self._a.append(float(self.get_depr(("data_%s" % name,), kwargs, locals()[name])))
        for name in ["par_b1", "par_b2", "par_b3", "par_b4", "par_b5"]:
            self._b.append(float(self.get_depr(("data_%s" % name,), kwargs, locals()[name])))
        
    def __str__(self):
        return "<AtomType %s (%s)>" % (self.name, id(self))
        
    # ------------------------------------------------------------
    #      Methods & Functions
    # ------------------------------------------------------------
    def get_atomic_scattering_factors(self, stl_range): 
        """
            Calculates the atomic scatter factor for a given range of 
            2*sin(θ) / λ values.
        """
        f = np.zeros(stl_range.shape)
        #if self.cache and self.cache.has_key(stl): #TODO: check if this would be an improvement or not
        #    return self.cache[stl]
        angstrom_range = stl_range*0.05
        for i in range(0,5):
             f += self._a[i] * np.exp(-self._b[i]*(angstrom_range)**2)
        f += self._c
        b = self.debye
        f = f * np.exp(-float(b) * (angstrom_range)**2)
        #if self.cache:
        #    self.cache[stl] = f
        return f
        

class Atom(ChildModel, ObjectListStoreChildMixin, Storable):
    """
        Atoms have an atom type plus structural parameters (position and proportion)
    """
    #MODEL INTEL:
    __parent_alias__ = 'component'
    __model_intel__ = [ #TODO add labels
        PropIntel(name="name",              inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True,  ctype=str,    refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="default_z",         inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True,  ctype=float,  refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="z",                 inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True,  ctype=float,  refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="pn",                inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True,  ctype=float,  refinable=False, storable=True,  observable=True,  has_widget=True),
        PropIntel(name="atom_type",         inh_name=None,  label="", minimum=None,  maximum=None,  is_column=True,  ctype=object, refinable=False, storable=False, observable=True,  has_widget=True),
        PropIntel(name="stretch_values",    inh_name=None,  label="", minimum=None,  maximum=None,  is_column=False, ctype=bool,   refinable=False, storable=False, observable=True,  has_widget=False),
    ]    
    
    #PROPERTIES:
    name = ""
    
    _default_z = 0
    def get_default_z_value(self): return self._default_z
    def set_default_z_value(self, value):
        if value != self._default_z:
            self._default_z = value
            self.liststore_item_changed()

    _stretch_values = False
    def get_stretch_values_value(self): return self._stretch_values
    def set_stretch_values_value(self, value):
        if value != self._stretch_values:
            self._stretch_values = value
            self.liststore_item_changed()
    
    def get_z_value(self):
        if self._stretch_values:
            sfactors = self.component.get_interlayer_stretch_factors()
            if sfactors:
                lattice_d, factor = sfactors
                return lattice_d + (self.default_z - lattice_d) * factor
        return self.default_z
    def set_z_value(self, value):
        self.default_z = value
    
    _pn = 0
    def get_pn_value(self): return self._pn
    def set_pn_value(self, value):
        if value != self._pn:
            self._pn = value
            self.liststore_item_changed()
    
    @property
    def weight(self):
        if self.atom_type!=None:
            return self.pn * self.atom_type.weight
        else:
            return 0.0
    
    _atom_type_index = None
    _atom_type_uuid = None
    _atom_type = None
    _atom_type_name = None
    def get_atom_type_value(self): return self._atom_type
    def set_atom_type_value(self, value):
        if self._atom_type is not None:
            self.relieve_model(self._atom_type)
        self._atom_type = value
        if self._atom_type is not None:
            self.observe_model(self._atom_type)
        self.liststore_item_changed()
         
    # ------------------------------------------------------------
    #      Initialisation and other internals
    # ------------------------------------------------------------
    def __init__(self, name=None, z=0, default_z=0, pn=None,
            atom_type=None, atom_type_index=None, atom_type_uuid=None, 
            atom_type_name=None, stretch_values=False, parent=None, **kwargs):  
        ChildModel.__init__(self, parent=parent)
        Storable.__init__(self)
               
        self.name = self.get_depr(("data_name",), kwargs, name or self.name)
        
        self.stretch_values = stretch_values
        self.default_z = default_z or self.get_depr(("data_z",), kwargs, z)
        self.pn = self.get_depr(("data_pn",), kwargs, pn or self._pn)
        self.atom_type = self.get_depr(("data_atom_type",), kwargs, atom_type)
        
        self._atom_type_uuid = atom_type_uuid or ""
        self._atom_type_name = atom_type_name or ""
        self._atom_type_index = atom_type_index if atom_type_index > -1 else None
         
    def __str__(self):
        return "<Atom %s(%s)>" % (self.name, repr(self))
    
    def _unattach_parent(self):
        self.atom_type = None
        ChildModel._unattach_parent(self)
         
    # ------------------------------------------------------------
    #      Notifications of observable properties
    # ------------------------------------------------------------
    @Observer.observe("removed", signal=True)
    def on_removed(self, model, prop_name, info):
        """
            This method observes the Atom types 'removed' signal,
            as such, if the AtomType gets removed from the parent project,
            it is also cleared from this Atom
        """
        if model == self.atom_type:
            self.atom_type = None
    
    # ------------------------------------------------------------
    #      Methods & Functions
    # ------------------------------------------------------------    
    def get_structure_factors(self, stl_range):
        if self.atom_type!=None:
            asf = self.atom_type.get_atomic_scattering_factors(stl_range)
        else:
            asf = 0.0
        return asf * self.pn * np.exp(2 * pi * self.z * stl_range * 1j)
    
    # ------------------------------------------------------------
    #      Input/Output stuff
    # ------------------------------------------------------------
    def resolve_json_references(self):    
        if self._atom_type_uuid!="":
            self.atom_type = pyxrd_object_pool.get_object(self._atom_type_uuid)
        elif self._atom_type_name!="":
            for atom_type in self.component.phase.project.data_atom_types.iter_objects():
                if atom_type.name == self._atom_type_name:
                    self.atom_type = atom_type
        elif self._atom_type_index is not None:
            warn("The use of object indeces is deprected since version 0.4. Please switch to using object UUIDs.", DeprecationWarning)
            self.atom_type = self.component.phase.project.data_atom_types.get_user_data_from_path((self._atom_type_index,))
        del self._atom_type_name
        del self._atom_type_uuid
        del self._atom_type_index

    def json_properties(self):
        from phases.models import Phase
        retval = Storable.json_properties(self)
        if self.component.phase.export_atom_types:
            retval["atom_type_name"] = self.atom_type.name if self.atom_type else ""
        else:
            retval["atom_type_uuid"] = self.atom_type.uuid if self.atom_type else ""
        return retval 
   
    @staticmethod
    def get_from_csv(filename, callback = None, parent=None):
        import csv
        atl_reader = csv.reader(open(filename, 'rb'), delimiter=',', quotechar='"') #TODO create csv dialect!
        header = True
        atoms = []
        
        types = dict()
        if parent != None:
            for atom_type in parent.phase.project.data_atom_types._model_data:
                if not atom_type.name in types:
                    types[atom_type.name] = atom_type
        
        for row in atl_reader:
            if not header and len(row)>=4:
                if len(row)==5:
                    name, z, def_z, pn, atom_type = row[0], float(row[1]), float(row[2]), float(row[3]), types[row[4]] if parent is not None else None
                else:
                    name, z, pn, atom_type = row[0], float(row[1]), float(row[2]), types[row[3]] if parent is not None else None
                    def_z = z
                
                if atom_type in types:
                    atom_type = types[atom_type]
                
                new_atom = Atom(name=name, z=z, default_z=def_z, pn=pn, atom_type=atom_type, parent=parent)
                atoms.append(new_atom)
                if callback is not None and callable(callback):
                    callback(new_atom)
                del new_atom
                
            header = False
        return atoms
        
    @staticmethod
    def save_as_csv(filename, atoms):
        import csv
        atl_writer = csv.writer(open(filename, 'wb'), delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        atl_writer.writerow(["Atom","z", "def_z", "pn","Element"])
        for item in atoms:
            atl_writer.writerow([item.name, item.z, item.default_z, item.pn, item.atom_type.name])
            
    pass #end of class
        
