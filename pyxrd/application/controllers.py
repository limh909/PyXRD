# coding=UTF-8
# ex:ts=4:sw=4:et=on

# Copyright (c) 2013, Mathijs Dumon
# All rights reserved.
# Complete license can be found in the LICENSE file.

import os
from os.path import basename, dirname

import gtk
import gobject

from pyxrd.gtkmvc import Controller

from pyxrd.data import settings

from pyxrd.generic.controllers import BaseController, DialogMixin
from pyxrd.generic.models import not_none
from pyxrd.generic.plot.controllers import MainPlotController

from pyxrd.project.controllers import ProjectController
from pyxrd.project.models import Project
from pyxrd.specimen.controllers import SpecimenController, MarkersController

from pyxrd.mixture.controllers import MixturesController
from pyxrd.phases.controllers import PhasesController
from pyxrd.atoms.controllers import AtomTypesController

class AppController (BaseController, DialogMixin):
    """
        Controller handling the main application interface.
        In essence this delegates actions to its child controllers for Project,
        Mixture, Specimen, Phase, Marker and Atoms actions. 
    """

    file_filters = Project.__file_filters__ + [ ("All Files", "*.*"), ]
    import_filters = Project.__import_filters__ + [ ("All Files", "*.*"), ]

    # ------------------------------------------------------------
    #      Initialization and other internals
    # ------------------------------------------------------------
    def __init__(self, model, view, spurious=False, auto_adapt=False, parent=None):
        """ Initializes an AppController with the given arguments. """
        super(AppController, self).__init__(model, view, spurious=spurious, auto_adapt=auto_adapt, parent=parent)

        # Plot controller:
        self.plot_controller = MainPlotController(self)
        view.setup_plot(self.plot_controller)

        # Child controllers:
        self.project = None
        self.specimen = None
        self.markers = None
        self.phases = None
        self.atom_types = None
        self.mixtures = None

        self.push_status_msg("Done.")

    def register_view(self, view):
        if self.model.project_loaded:
            self.update_sensitivities()
            view.set_layout_mode(self.model.current_project.layout_mode)
        else:
            view.set_layout_mode(settings.DEFAULT_LAYOUT)

    def set_model(self, model):
        super(self, AppController).set_model(model)
        self.reset_project_controller()

    def reset_project_controller(self):
        self.view.reset_all_views()
        self.project = ProjectController(model=self.model.current_project, view=self.view.project, parent=self)
        self.phases = PhasesController(model=self.model.current_project, view=self.view.phases, parent=self)
        self.atom_types = AtomTypesController(model=self.model.current_project, view=self.view.atom_types, parent=self)
        self.mixtures = MixturesController(model=self.model.current_project, view=self.view.mixtures, parent=self)
        self.reset_specimen_controller()

    def reset_specimen_controller(self):
        if self.model.specimen_selected:
            specimen_view = self.view.reset_child_view("specimen")
            self.specimen = SpecimenController(model=self.model.current_specimen, view=specimen_view, parent=self)
            markers_view = self.view.reset_child_view("markers")
            self.markers = MarkersController(model=self.model.current_specimen, view=markers_view, parent=self)
        else:
            self.specimen = None
            self.markers = None

    # ------------------------------------------------------------
    #      Notifications of observable properties
    # ------------------------------------------------------------
    @Controller.observe("needs_plot_update", signal=True)
    def notif_needs_plot_update(self, model, prop_name, info):
        # This is emitted by the Application model, in effect it is either a
        #  forwarded data_changed or visuals_changed signal coming from the
        #  project model.
        self.idle_redraw_plot()

    @Controller.observe("current_project", assign=True, after=True)
    def notif_project_update(self, model, prop_name, info):
        self.reset_project_controller()
        self.view.update_project_sensitivities(self.model.project_loaded)
        self.set_layout_mode(self.model.current_project.layout_mode)
        self.update_title()

    @Controller.observe("current_specimen", assign=True, after=True)
    @Controller.observe("current_specimens", assign=True, after=True)
    def notif_specimen_changed(self, model, prop_name, info):
        self.reset_specimen_controller()
        self.view.update_specimen_sensitivities(
            self.model.single_specimen_selected,
            self.model.multiple_specimens_selected
        )
        self.idle_redraw_plot()

    # ------------------------------------------------------------
    #      View updating
    # ------------------------------------------------------------

    _idle_redraw_id = None
    def idle_redraw_plot(self):
        """Adds a redraw plot function as 'idle' action to the main GTK loop."""
        self._idle_redraw_id = gobject.idle_add(self.redraw_plot)

    @BaseController.status_message("Updating display...")
    def redraw_plot(self):
        """Updates the plot"""
        self.plot_controller.update(
            clear=True,
            project=self.model.current_project,
            specimens=self.model.current_specimens[::-1]
        )
        # If we still have an idle id, try to remove it and clear the attribute:
        if self._idle_redraw_id is not None:
            gobject.source_remove(self._idle_redraw_id)
            self._idle_redraw_id = None

    def update_title(self):
        """Convenience method for setting the application view's title"""
        self.view.set_title(self.model.current_project.name)

    def update_sensitivities(self):
        """Convenience method for updating the application view's sensitivities"""
        self.view.update_project_sensitivities(self.model.project_loaded)
        self.view.update_specimen_sensitivities(
            self.model.single_specimen_selected,
            self.model.multiple_specimens_selected
        )

    def set_layout_mode(self, mode):
        """Convenience method for updating the application view's layout mode"""
        self.view.set_layout_mode(mode)

    # ------------------------------------------------------------
    #      Loading and saving of projects
    # ------------------------------------------------------------
    def save_project(self, filename=None):
        # Set the filename to the current location if None or "" was given:
        filename = filename or self.model.current_filename

        # Try to save the project:
        with self.ui_error_handler("An error has occurred while saving!"):
            self.model.current_project.save_object(filename)

        # Set the current filename property and update the title
        self.model.current_filename = filename
        self.update_title()

    def save_project_as(self, title="Save project as"):
        def on_accept(dialog):
            self.save_project(filename=self.extract_filename(dialog))
        suggest_name, suggest_folder = None, None
        if self.model.current_filename is not None:
            # Set the name and directory of the file dialog to the current
            # project location:
            suggest_name = basename(self.model.current_filename)
            suggest_folder = dirname(self.model.current_filename)
        self.run_save_dialog(title=title,
                             suggest_name=suggest_name,
                             suggest_folder=suggest_folder,
                             on_accept_callback=on_accept,
                             parent=self.view.get_top_widget())

    def open_project(self, filename):
        # Try to load the project:
        with self.ui_error_handler("An error has occurred.\n Your project was not loaded!"):
            self.model.current_project = Project.load_object(filename, parent=self.model)

        # Set the current filename property and update the title
        self.model.current_filename = filename
        self.update_title()

    def load_project(self, title, confirm_msg, action=None, filters=None):
        """Convenience function for loading projects from different sources
        following similar user interaction paths"""
        action = not_none(action, self.open_project)
        filter = not_none(filters, self.file_filters)
        def on_open_project(confirm_dialog):
            def on_accept(dialog):
                action(self.extract_filename(dialog))
            self.run_load_dialog(
                title=title,
                on_accept_callback=on_accept,
                filters=filters,
                parent=self.view.get_top_widget())
        if self.model.current_project and self.model.current_project.needs_saving:
            self.run_confirmation_dialog(
                confirm_msg,
                on_open_project,
                parent=self.view.get_top_widget())
        else:
            on_open_project(None)

    def new_project(self):
        # Create a new project
        self.model.current_project = Project(parent=self.model)

        # Set the current filename property and update the title
        self.model.current_filename = None
        self.update_title()

        # Show the edit project dialog
        self.view.project.present()

    def import_project_from_xml(self, filename):
        with self.ui_error_handler("An error has occurred.\n Your project was not imported!"):
            self.model.current_project = Project.create_from_sybilla_xml(filename, parent=self.model)

        self.model.current_filename = None
        self.update_title()
        self.view.project.present()

    # ------------------------------------------------------------
    #      GTK Signal handlers - general
    # ------------------------------------------------------------
    def on_manual_activate(self, widget, data=None):
        try:
            import webbrowser
            webbrowser.open(settings.MANUAL_URL)
        except:
            pass # ignore errors
        return True

    def on_about_activate(self, widget, data=None):
        # self.run_dialog(self.view["about_window"], destroy=True)
        self.view["about_window"].show()
        return True

    def on_main_window_delete_event(self, widget, event):
        def on_accept(dialog):
            gtk.main_quit()
            return False
        def on_reject(dialog):
            return True
        if self.model.current_project and self.model.current_project.needs_saving:
            return self.run_confirmation_dialog(
                "The current project has unsaved changes,\n"
                "are you sure you want to quit?",
                on_accept, on_reject,
                parent=self.view.get_top_widget())
        else:
            return on_accept(None)

    def on_menu_item_quit_activate (self, widget, data=None):
        self.view.get_toplevel().destroy()
        return True

    def on_refresh_graph(self, event):
        if self.model.current_project:
            self.model.current_project.update_all()

    def on_save_graph(self, event):
        filename = None
        if self.model.single_specimen_selected:
            filename = os.path.splitext(self.model.current_specimen.name)[0]
        else:
            filename = self.model.current_project.name
        self.plot_controller.save(
            parent=self.view.get_toplevel(),
            suggest_name=filename,
            num_specimens=len(self.model.current_specimens),
            offset=self.model.current_project.display_plot_offset)

    def on_sample_point(self, event):
        """
            Sample a point on the plot and display the (calculated and)
            experimental data values in an information dialog.
        """
        def parse_x_pos(x_pos):
            exp_y = self.model.current_specimen.experimental_pattern.xy_store.get_y_at_x(x_pos)
            calc_y = self.model.current_specimen.calculated_pattern.xy_store.get_y_at_x(x_pos)
            message = "Sampled point:\n"
            message += "\tExperimental data:\t( %.4f , %.4f )\n"
            if self.model.current_project.layout_mode == "FULL":
                message += "\tCalculated data:\t\t( %.4f , %.4f )"
            message = message % (x_pos, exp_y, x_pos, calc_y)
            self.run_information_dialog(message, parent=self.view.get_toplevel())

        self.plot_controller.get_user_x_coordinate(parse_x_pos)

    # ------------------------------------------------------------
    #      GTK Signal handlers - Project related
    # ------------------------------------------------------------
    @BaseController.status_message("Creating new project...", "new_project")
    def on_new_project_activate(self, widget, data=None):
        def on_accept(dialog):
            print "Creating new project..."
            self.new_project()
        if self.model.current_project and self.model.current_project.needs_saving:
            self.run_confirmation_dialog(
                "The current project has unsaved changes,\n"
                "are you sure you want to create a new project?",
                on_accept, parent=self.view.get_top_widget())
        else:
            on_accept(None)

    @BaseController.status_message("Displaying project data...", "edit_project")
    def on_edit_project_activate(self, widget, data=None):
        self.view.project.present()

    @BaseController.status_message("Open project...", "open_project")
    def on_open_project_activate(self, widget, data=None):
        """Open an existing project. Asks the user if (s)he's sure when an 
        unsaved project is loaded."""
        self.load_project(
            title="Open project",
            confirm_msg="The current project has unsaved changes,\n"
                "are you sure you want to load another project?",
            action=self.open_project,
        )

    @BaseController.status_message("Import Sybilla XML...", "import_project_xml")
    def on_import_project_sybilla_activate(self, widget, data=None, title="Import Sybilla XML"):
        """Import an existing Sybilla project from an XML file. Asks the user if
        (s)he's sure when an unsaved project is loaded."""
        self.load_project(
            title="Import project",
            confirm_msg="The current project has unsaved changes,\n"
                "are you sure you want to create a new project?",
            action=self.import_project_from_xml,
            filters=self.import_filters
        )

    @BaseController.status_message("Save project...", "save_project")
    def on_save_project_activate(self, widget, *args):
        if not self.model.current_filename:
            self.save_project_as(title="Save project")
        else:
            self.save_project()

    @BaseController.status_message("Save project...", "save_project")
    def on_save_project_as_activate(self, widget, *args):
        self.save_project_as()

    # ------------------------------------------------------------
    #      GTK Signal handlers - Mixtures related
    # -----------------------------------------------------------
    def on_edit_mixtures(self, widget, data=None):
        if self.model.project_loaded:
            self.view.mixtures.present()
        pass

    # ------------------------------------------------------------
    #      GTK Signal handlers - Specimen related
    # ------------------------------------------------------------
    def on_edit_specimen_activate(self, event):
        if self.model.single_specimen_selected:
            self.view.specimen.present()
        return True

    def on_add_specimen_activate(self, event):
        self.project.add_specimen()
        return True

    def on_add_multiple_specimens(self, event):
        self.project.import_multiple_specimen()
        return True

    def on_del_specimen_activate(self, event):
        self.project.delete_selected_specimens()
        return True

    def on_replace_specimen_data_activate(self, event):
        if self.model.single_specimen_selected:
            self.specimen.on_replace_experimental_data()
        return True

    def on_export_specimen_data_activate(self, event):
        if self.model.single_specimen_selected:
            self.specimen.on_export_experimental_data()
        return True

    def on_remove_background(self, event):
        if self.model.single_specimen_selected:
            self.specimen.remove_background()
        return True

    def on_smooth_data(self, event):
        if self.model.single_specimen_selected:
            self.specimen.smooth_data()
        return True

    def on_add_noise(self, event):
        if self.model.single_specimen_selected:
            self.specimen.add_noise()
        return True

    def on_shift_data(self, event):
        if self.model.single_specimen_selected:
            self.specimen.shift_data()
        return True

    def on_strip_peak(self, event):
        if self.model.single_specimen_selected:
            self.specimen.strip_peak()
        return True

    # ------------------------------------------------------------
    #      GTK Signal handlers - Phases related
    # ------------------------------------------------------------
    def on_edit_phases_activate(self, event):
        if self.model.project_loaded:
            self.view.phases.present()
        return True

    # ------------------------------------------------------------
    #      GTK Signal handlers - Atom Types related
    # ------------------------------------------------------------
    def on_edit_atom_types_activate(self, event):
        if self.model.project_loaded:
            self.view.atom_types.present()
        return True

    # ------------------------------------------------------------
    #      GTK Signal handlers - Markers related
    # ------------------------------------------------------------
    def on_edit_markers_activate(self, event):
        if self.model.current_specimen is not None:
            self.view.markers.present()
        return True

    pass # end of class

