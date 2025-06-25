# -*- coding: utf-8 -*-

"""
@author: Nandish Patel

Copyright © 2025 Nandish Patel, Delmic

This file is part of Odemis.

Odemis is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License version 2 as published by the Free
Software Foundation.

Odemis is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
Odemis. If not, see http://www.gnu.org/licenses/.

"""
import math
from typing import List

import wx
from wx.grid import GridCellBoolEditor, GridCellFloatEditor, GridCellNumberEditor

import odemis.gui.model as guimod
from odemis.gui.comp.fastem_roa import FastEMTOA
from odemis.gui.comp.fastem_user_settings_panel import (
    CONTROL_CONFIG,
    DWELL_TIME_SINGLE_BEAM,
)
from odemis.gui.cont.fastem_project_grid import TOAColumnNames
from odemis.gui.cont.fastem_project_grid_base import (
    Column,
    GridBase,
    GridCellFloatRangeEditor,
    Row,
)
from odemis.gui.cont.tabs.tab import Tab
from odemis.gui.util import call_in_wx_main
from odemis.util import units
from odemis.util.filename import make_compliant_string


class TOARow(Row):
    """Class representing a row in the TOA (Region of Interest) grid."""

    def __init__(self, data, roa, index=-1):
        super().__init__(data, roa, index)

    def to_dict(self) -> dict:
        """
        Converts the TOARow instance to a dictionary format.

        :return: (dict) The TOARow data in dictionary format.
        """
        return {
            "index": self.index,
            "data": self.data,
            "roa": (
                self.roa.to_dict() if hasattr(self.roa, "to_dict") else str(self.roa)
            ),  # Assuming roa has a to_dict method or can be stringified
        }

    @staticmethod
    def from_dict(toa: dict, tab_data):
        """
        Creates a TOARow instance from a dictionary.

        :param toa: (dict) Dictionary containing the TOA row data.
        :param tab_data: (MicroscopyGUIData) Data related to the tab.
        :return: (TOARow) The created TOARow instance.
        """
        index = int(toa["index"])
        data = toa["data"]
        roa = FastEMTOA.from_dict(toa["roa"], tab_data)
        toa_row = TOARow(data, roa, index)
        if toa_row.data[TOAColumnNames.FIELDS.value] == "1":
            toa_row.roa.shape.grid_rects = toa_row.roa.field_rects
            toa_row.roa.shape.fill_grid.value = True
        return toa_row

    @staticmethod
    def find_next_slice_index(name: str, rows: List[Row]) -> int:
        """
        Finds the next available index for the given name in the list of rows.

        :param name: (str) The name for which the index is to be found.
        :param rows: (list) The list of existing rows.
        :return: (int) The next available index for the given name.
        """
        used_indices = {
            int(row.data[TOAColumnNames.SLICE_IDX.value])
            for row in rows
            if row.data[TOAColumnNames.NAME.value] == name
        }
        # Find the smallest missing index
        next_index = 0
        while next_index in used_indices:
            next_index += 1
        return next_index

    @staticmethod
    def is_unique_name_slice_idx(name: str, slice_idx: int, rows: List[Row]) -> bool:
        """
        Checks if the given index is unique for the specified name in the list of rows.

        :param name: (str) The name to check for uniqueness.
        :param slice_idx: (int) The index to check for uniqueness.
        :param rows: (list) The list of existing rows.
        :return: (bool) True if the index is unique for the given name, False otherwise.
        """
        for row in rows:
            if (
                row.data[TOAColumnNames.NAME.value] == name
                and row.data[TOAColumnNames.SLICE_IDX.value] == slice_idx
            ):
                return False
        return True

    @staticmethod
    def unfill_shapes_grid(col: Column, grid: GridBase):
        """
        Sets the fill_grid flag for all rows shapes to False if it was previously True.

        :param col: (Column) The column that is affected.
        :param grid: (GridBase) The grid instance that contains the rows.
        """
        for row in grid.rows:
            if row.roa.shape.fill_grid.value:
                row.data[TOAColumnNames.FIELDS.value] = ""
                grid.SetCellValue(row.index, col.index, "")
                row.roa.shape.fill_grid.value = False

    @call_in_wx_main
    def update_shape_grid_rects(self, update: bool = True):
        """
        Update the TOA shape's (EditableShape) grid rectangles.

        :param update: Flag which states if the shape's grid rectangles need to be updated or not.
        """
        if update:
            self.roa.calculate_field_indices()
            self.roa.calculate_grid_rects()
            self.roa.shape.grid_rects = self.roa.field_rects
        self.roa.shape.fill_grid.value = update
        self.roa.shape.cnvs.request_drawing_update()

    def update_data(self):
        """
        Updates the row data based on the TOA.

        This method updates the position, size, rotation, and field data in the row
        based on the shape associated with the TOA. If the fields value is "1", it
        recalculates the grid rectangles and refreshes the drawing.
        """
        posx, posy = self.roa.shape.get_position()
        sizex, sizey = self.roa.shape.get_size()
        sizex = units.readable_str(sizex, unit="m", sig=3)
        sizey = units.readable_str(sizey, unit="m", sig=3)
        current_sample = self.roa.main_data.current_sample.value
        scintillator = current_sample.find_closest_scintillator((posx, posy))
        scintillator_num = 0
        if scintillator is not None:
            scintillator_num = scintillator.number
        self.data[TOAColumnNames.POSX.value] = round(posx, 9)
        self.data[TOAColumnNames.POSY.value] = round(posy, 9)
        self.data[TOAColumnNames.SIZEX.value] = sizex
        self.data[TOAColumnNames.SIZEY.value] = sizey
        self.data[TOAColumnNames.ROT.value] = round(math.degrees(self.roa.shape.rotation))
        self.data[TOAColumnNames.SCINTILLATOR_NUM.value] = scintillator_num
        if self.data[TOAColumnNames.FIELDS.value] == "1":
            self.update_shape_grid_rects()

    def on_cell_changing(self, new_value: str, row: int, col: int, grid: GridBase) -> str:
        """
        Handles changes in cell values and updates associated data and TOA.

        :param new_value: (str) The new value to set in the cell. The cell editor
            class will make sure that a user can only input value in the cell of
            the correct type.
        :param row: (int) The index of the row being modified.
        :param col: (int) The index of the column being modified.
        :param grid: (GridBase) The grid instance that contains the row.
        :return: (str) The value to set in the cell.
        """
        value_to_set = new_value
        rows = grid.rows
        col = grid.columns[col]
        if col.label == TOAColumnNames.NAME.value:
            value_to_set = make_compliant_string(value_to_set)
            if not value_to_set:
                value_to_set = "TOA"
            current_slice_idx = self.data[TOAColumnNames.SLICE_IDX.value]
            if not TOARow.is_unique_name_slice_idx(
                value_to_set, current_slice_idx, rows
            ):
                new_slice_idx = TOARow.find_next_slice_index(value_to_set, rows)
                self.data[TOAColumnNames.SLICE_IDX.value] = new_slice_idx
                self.roa.slice_index.value = new_slice_idx
                slice_index_col = grid.get_column_by_label(
                    TOAColumnNames.SLICE_IDX.value
                )
                grid.SetCellValue(row, slice_index_col.index, str(new_slice_idx))
            self.data[TOAColumnNames.NAME.value] = value_to_set
            self.roa.shape.name.value = (
                f"{value_to_set}_{self.data[TOAColumnNames.SLICE_IDX.value]}"
            )
            self.roa.name.value = value_to_set
        elif col.label == TOAColumnNames.SLICE_IDX.value:
            current_name = self.data[TOAColumnNames.NAME.value]
            if not TOARow.is_unique_name_slice_idx(
                current_name, int(value_to_set), rows
            ):
                new_slice_idx = TOARow.find_next_slice_index(current_name, rows)
                value_to_set = str(new_slice_idx)
            self.data[TOAColumnNames.SLICE_IDX.value] = int(value_to_set)
            self.roa.slice_index.value = int(value_to_set)
            self.roa.shape.name.value = (
                f"{self.data[TOAColumnNames.NAME.value]}_{value_to_set}"
            )
        elif col.label == TOAColumnNames.POSX.value:
            if not value_to_set:
                value_to_set = str(self.data[TOAColumnNames.POSX.value])
            else:
                posy = self.data[TOAColumnNames.POSY.value]
                self.data[TOAColumnNames.POSX.value] = posx = float(value_to_set)
                self.roa.shape.move_to((posx, posy))
                self.roa.shape.cnvs.request_drawing_update()
        elif col.label == TOAColumnNames.POSY.value:
            if not value_to_set:
                value_to_set = str(self.data[TOAColumnNames.POSY.value])
            else:
                posx = self.data[TOAColumnNames.POSX.value]
                self.data[TOAColumnNames.POSY.value] = posy = float(value_to_set)
                self.roa.shape.move_to((posx, posy))
                self.roa.shape.cnvs.request_drawing_update()
        elif col.label == TOAColumnNames.ROT.value:
            self.data[TOAColumnNames.ROT.value] = rot = int(value_to_set)
            self.roa.shape.set_rotation(math.radians(rot))
            self.roa.shape.cnvs.request_drawing_update()
        elif col.label == TOAColumnNames.CONTRAST.value:
            self.data[TOAColumnNames.CONTRAST.value] = float(value_to_set)
        elif col.label == TOAColumnNames.BRIGHTNESS.value:
            self.data[TOAColumnNames.BRIGHTNESS.value] = float(value_to_set)
        elif col.label == TOAColumnNames.DWELL_TIME.value:
            self.data[TOAColumnNames.DWELL_TIME.value] = float(value_to_set)
        elif col.label == TOAColumnNames.FIELDS.value:
            self.data[TOAColumnNames.FIELDS.value] = value_to_set
            # Allow only one row shape's grid to be drawn to reduce the overhead
            # if the size of the shape is large
            TOARow.unfill_shapes_grid(col, grid)
            self.update_shape_grid_rects(update=value_to_set == "1")
        return value_to_set


class FastEMProjectTOAsTab(Tab):
    """Tab class for displaying and interacting with TOAs data for a project."""

    def __init__(self, name, button, panel, main_frame, main_data):

        self.tab_data = guimod.MicroscopyGUIData(main_data)
        super().__init__(name, button, panel, main_frame, self.tab_data)
        # Flag to indicate the tab has been fully initialized or not. Some initialisation
        # need to wait for the tab to be shown on the first time.
        self._initialized_after_show = False

        self.grid = GridBase(panel, size=panel.Parent.Size)
        dwell_time_config = CONTROL_CONFIG[DWELL_TIME_SINGLE_BEAM]
        self.columns = [
            Column(0, TOAColumnNames.NAME.value),
            Column(
                1,
                TOAColumnNames.SLICE_IDX.value,
                editor_cls=GridCellNumberEditor,
                editor_args={"min": 0, "max": 1000000},
            ),
            Column(2, TOAColumnNames.FIELDS.value, editor_cls=GridCellBoolEditor),
            Column(
                3,
                TOAColumnNames.CONTRAST.value,
                editor_cls=GridCellFloatRangeEditor,
                editor_args={"min": 0., "max": 1., "precision": 4},
            ),
            Column(
                4,
                TOAColumnNames.BRIGHTNESS.value,
                editor_cls=GridCellFloatRangeEditor,
                editor_args={"min": 0., "max": 1., "precision": 4},
            ),
            Column(
                5,
                TOAColumnNames.DWELL_TIME.value,
                editor_cls=GridCellFloatRangeEditor,
                editor_args={
                    "min": dwell_time_config["min_val"] * 1e6,  # [µs]
                    "max": dwell_time_config["max_val"] * 1e6,  # [µs]
                    "precision": 4
                },
            ),
            Column(
                6,
                TOAColumnNames.SCINTILLATOR_NUM.value,
                editor_cls=GridCellNumberEditor,
                is_read_only=True,
            ),
            Column(
                7,
                TOAColumnNames.POSX.value,
                editor_cls=GridCellFloatEditor,
                editor_args={"precision": 9},
            ),
            Column(
                8,
                TOAColumnNames.POSY.value,
                editor_cls=GridCellFloatEditor,
                editor_args={"precision": 9},
            ),
            Column(
                9,
                TOAColumnNames.SIZEX.value,
                editor_cls=GridCellFloatEditor,
                is_read_only=True,
            ),
            Column(
                10,
                TOAColumnNames.SIZEY.value,
                editor_cls=GridCellFloatEditor,
                is_read_only=True,
            ),
            Column(
                11,
                TOAColumnNames.ROT.value,
                editor_cls=GridCellNumberEditor,
                editor_args={"min": 0, "max": 360},
            ),
        ]
        self.grid.set_columns(self.columns)

        self.panel.Bind(wx.EVT_SIZE, self._on_panel_size)

    def create_grid(self) -> GridBase:
        """
        Creates and configures a new grid for displaying data.

        :return: (GridBase) A configured instance of the grid.

        Note:
            The grid is not displayed immediately but is prepared for further manipulation
            or data population before being shown.
        """
        grid = GridBase(self.panel, size=self.panel.Parent.Size)
        grid.set_columns(self.columns)
        grid.Hide()
        return grid

    def _on_panel_size(self, evt):
        """Adjusts the grid size when the panel size changes."""
        self.grid.SetSize(self.panel.Parent.Size)
        self.grid.Layout()
        self.grid.Refresh()

    def Show(self, show=True):
        super().Show(show)

        if show and not self._initialized_after_show:
            self._initialized_after_show = True

    @classmethod
    def get_display_priority(cls, main_data):
        # Tab is used only for FastEM
        if main_data.role in ("mbsem",):
            return 2
        else:
            return None
