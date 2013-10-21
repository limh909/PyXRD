# coding=UTF-8
# ex:ts=4:sw=4:et=on

# Copyright (c) 2013, Mathijs Dumon
# All rights reserved.
# Complete license can be found in the LICENSE file.

from pyxrd.gtkmvc.model import Observer, Signal

from pyxrd.generic.models import PyXRDModel
from pyxrd.generic.models.metaclasses import pyxrd_object_pool

class AppModel(PyXRDModel):
    """
        Simple model that stores the state of the application window.
        Should never be made persistent.
        
        Attributes:
            needs_plot_update: a gtkmvc.Signal to indicate the plot needs an
                update. This models listens for the 'needs_update' signal on the
                loaded project and propagates this accordingly.
            current_project: the currently loaded project
            statistics_visble: a boolean indicating whether or not statistic
                should be visible
            current_specimen: the currently selected specimen, is None if more
                than one specimen is selected.
            current_specimens: a list of currently selected specimens, is never
                None, even if only one specimen is selected.
            single_specimen_selected: a boolean indicating whether or not a
                single specimen is selected
            multiple_specimen_selected: a boolean indicating whether or not
                multiple specimen are selected
    """
    # MODEL INTEL:
    __observables__ = (
        "current_project",
        "current_specimen",
        "current_specimens",
        "statistics_visible",
        "needs_plot_update"
    )

    # SIGNALS:
    needs_plot_update = None

    # PROPERTIES:
    _current_project = None
    def get_current_project_value(self):
        return self._current_project
    def set_current_project_value(self, value):
        if self._current_project != None: self.relieve_model(self._current_project)
        self._current_project = value
        pyxrd_object_pool.clear()
        if self._current_project != None: self.observe_model(self._current_project)
    current_filename = None

    _statistics_visible = None
    def set_statistics_visible_value(self, value): self._statistics_visible = value
    def get_statistics_visible_value(self):
        return self._statistics_visible and self.current_specimen != None and self.current_project.layout_mode != 1

    _current_specimen = None
    def get_current_specimen_value(self): return self._current_specimen
    def set_current_specimen_value(self, value):
        self._current_specimens = [value]
        self._current_specimen = value

    _current_specimens = []
    def get_current_specimens_value(self): return self._current_specimens
    def set_current_specimens_value(self, value):
        if value == None:
            value = []
        self._current_specimens = value
        if len(self._current_specimens) == 1:
            self._current_specimen = self._current_specimens[0]
        else:
            self._current_specimen = None

    @property
    def single_specimen_selected(self):
        return bool(self.current_specimen != None or self.current_specimens == [])

    @property
    def multiple_specimens_selected(self):
        return bool(len(self.current_specimens) > 1)


    # ------------------------------------------------------------
    #      Initialisation and other internals
    # ------------------------------------------------------------
    def __init__(self, project=None):
        """ Initializes the AppModel with the given Project. """
        super(AppModel, self).__init__()
        self.needs_plot_update = Signal()
        self.current_project = project
        self._statistics_visible = False

    # ------------------------------------------------------------
    #      Notifications of observable properties
    # ------------------------------------------------------------
    @Observer.observe("needs_update", signal=True)
    def notify_needs_update(self, model, prop_name, info):
        self.needs_plot_update.emit()

    pass # end of class