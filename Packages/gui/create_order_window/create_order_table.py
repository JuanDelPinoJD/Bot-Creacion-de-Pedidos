import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style
import pandas as pd
import numpy as np
from tkinter import filedialog


class CreateOrderTable:
    """Clase para la tabla incial donde se escribe la orden manualmente"""

    def __init__(self, parent_window: tk.Frame, orders: pd.DataFrame = None, headers: list = None):
        self.parent_window = parent_window
        if orders is not None:
            headers = list(orders)
        elif headers is not None:
            self.headers = headers
        self.frame = ttk.Frame(parent_window)
        self.frame.bind('<Return>', self.on_enter)
        for col in range(len(headers)):
            entry = ttk.Label(self.frame, width=20, text=headers[col], style='primary.Inverse.TLabel')
            entry.grid(row=0, column=col, sticky='ew', padx=1)
        if orders is not None:
            self.entries = []
            for index in orders.index:
                row = []
                for col in range(len(orders.columns)):
                    text = orders[orders.columns[col]][index]
                    entry = ttk.Entry(self.frame, width=20)
                    entry.insert(0, text)
                    entry.grid(row=index + 1, column=col)
                    row.append(entry)
                self.entries.append(row)
        else:
            self.entries = []
            for index in range(1):
                row = []
                for col in range(len(headers)):
                    if col in [1, 6]:
                        if col == 1:
                            text = 'manual'
                        elif col == 6:
                            text = '1'
                        entry = ttk.Label(self.frame, text=text, width=20, background='grey',
                                          padding=5, relief='sunken')
                        entry.grid(row=index + 1, column=col)
                        row.append(entry)
                    else:
                        entry = ttk.Entry(self.frame, width=20)
                        entry.grid(row=index + 1, column=col)
                        row.append(entry)
                self.entries.append(row)

        self.latest_index = 1
        self.add_button = ttk.Button(self.frame, text='Agregar entrada',
                                     command=lambda: [self.add_row()])
        self.add_button.grid(row=self.latest_index + 1, column=len(headers) - 1, sticky='e', pady=10)
        self.delete_button = ttk.Button(self.frame, text='Eliminar entrada', style='danger.TButton',
                                        command=lambda: [self.delete_row()])

    def add_row(self):
        """Funcion que agrega una fila en la tabla"""
        order_number = self.entries[0][0].get()
        reference = self.entries[0][2].get()
        row = []
        for col in range(len(self.headers)):
            if col in [1, 6]:
                if col == 1:
                    text = 'manual'
                elif col == 6:
                    text = '1'
                entry = ttk.Label(self.frame, text=text, width=20, background='grey',
                                  padding=5, relief='sunken')
                entry.grid(row=self.latest_index + 1, column=col)
                row.append(entry)
            else:
                entry = ttk.Entry(self.frame, width=20)
                if col == 0:
                    entry.insert(0, order_number)
                elif col == 2:
                    entry.insert(0, reference)
                entry.grid(row=self.latest_index + 1, column=col)
                row.append(entry)
        self.entries.append(row)
        self.latest_index = self.latest_index + 1
        self.add_button.grid(row=self.latest_index + 1, column=len(self.headers) - 1, sticky='e', pady=10)
        if self.latest_index >= 2:
            self.delete_button.grid(row=self.latest_index + 1, column=len(self.headers) - 2, sticky='e', pady=10)

    def delete_row(self):
        """Funcion que elimina una fila en la tabla"""
        row = self.latest_index - 1
        for col in range(len(self.headers)):
            self.entries[row][col].destroy()
        self.entries.remove(self.entries[row])
        self.latest_index = self.latest_index - 1
        self.add_button.grid(row=self.latest_index + 1, column=len(self.headers) - 1, sticky='e', pady=10)
        if self.latest_index < 2:
            self.delete_button.grid_forget()
        if self.latest_index >= 2:
            self.delete_button.grid(row=self.latest_index + 1, column=len(self.headers) - 2, sticky='e', pady=10)

    def update_cells(self):
        """Funcion que actualiza los valores de order number y
        reference para que tengas todos los mismos valores"""
        order_number = self.entries[0][0].get()
        reference = self.entries[0][2].get()
        index = 0
        for row in self.entries:
            for col in range(len(row)):
                if col == 0:
                    self.entries[index][col].delete(0, 1000)
                    self.entries[index][col].insert(0, order_number)
                elif col == 2:
                    self.entries[index][col].delete(0, 1000)
                    self.entries[index][col].insert(0, reference)
            index = index + 1

    def on_enter(self, event):
        """Evento que hace que se selccione la selda inferior a la selccionada
        al presionar enter, tambien hace que se cree una fila en caso de que esta sea
        la ultima"""
        focus = self.parent_window.focus_get()
        index = 0
        for row in self.entries:
            for col in range(len(row)):
                e = self.entries[index][col]
                if e == focus:
                    try:
                        self.entries[index + 1][col].focus_set()
                    except IndexError:
                        self.add_row()
                        self.entries[index + 1][col].focus_set()
            index = index + 1

    def read_table(self) -> pd.DataFrame:
        order_numbers = []
        clients = []
        references = []
        quantities = []
        ship_out_dates = []
        arrival_dates = []
        confidences = []
        index = 0
        for row in self.entries:
            for col in range(len(row)):
                if col not in [1, 6]:
                    value = self.entries[index][col].get()
                    if value in ['', ' ']:
                        value = np.NaN
                if col == 0:
                    order_numbers.append(value)
                elif col == 1:
                    clients.append('manual')
                elif col == 2:
                    references.append(value)
                elif col == 3:
                    quantities.append(value)
                elif col == 4:
                    ship_out_dates.append(value)
                elif col == 5:
                    arrival_dates.append(value)
                elif col == 6:
                    confidences.append('1')
            index = index + 1

        data = {"order_number": order_numbers,
                "client": clients,
                "reference": references,
                "quantity": quantities,
                'ship_out_date': ship_out_dates,
                'arrival_date': arrival_dates,
                "confidence": confidences}
        self.orders = pd.DataFrame(data, dtype=str)
        return self.orders

    def save_table(self):
        from ...constants import exports_folder
        file = filedialog.asksaveasfile(mode='w', defaultextension=".xlsx",
                                        initialfile='export', initialdir=exports_folder,
                                        filetypes=(("excel files", "*.xlsx"), ("all files", "*.*")))
        try:
            save_root = file.name
            orders = self.read_table()
            orders.to_excel(save_root, index=False)
        except AttributeError:
            return

    def import_table(self):
        from ...constants import exports_folder
        file_root = filedialog.askopenfilename(initialdir=exports_folder,
                                               filetypes=(("excel files", "*.xlsx"), ("all files", "*.*")))
        try:
            data = pd.read_excel(file_root, dtype=str)
            orders = pd.DataFrame(data, dtype=str)
        except FileNotFoundError:
            return
        # Borrar tabla existente
        for row in self.entries:
            for entry in row:
                entry.destroy()

        # Escribir la tabla importada
        self.entries = []
        for index in range(1):
            row = []
            for col in range(len(self.headers)):
                if col in [1, 6]:
                    if col == 1:
                        text = 'manual'
                    elif col == 6:
                        text = '1'
                    entry = ttk.Label(self.frame, text=text, width=20, background='grey',
                                      padding=5, relief='sunken')
                    entry.grid(row=index + 1, column=col)
                    row.append(entry)
                else:
                    entry = ttk.Entry(self.frame, width=20)
                    entry.grid(row=index + 1, column=col)
                    row.append(entry)
            self.entries.append(row)
        self.latest_index = 1
        for index in orders.index:
            if index > 0:
                self.add_row()

        index = 0
        for row in self.entries:
            for col in range(len(row)):
                if col not in [1, 6]:
                    text = str(orders[orders.columns[col]][index])
                    self.entries[index][col].insert(0, text)
            index = index + 1

    def clear_table(self):
        # Borrar tabla existente
        for row in self.entries:
            for entry in row:
                entry.destroy()
        self.entries = []
        for index in range(1):
            row = []
            for col in range(len(self.headers)):
                if col in [1, 6]:
                    if col == 1:
                        text = 'manual'
                    elif col == 6:
                        text = '1'
                    entry = ttk.Label(self.frame, text=text, width=20, background='grey',
                                      padding=5, relief='sunken')
                    entry.grid(row=index + 1, column=col)
                    row.append(entry)
                else:
                    entry = ttk.Entry(self.frame, width=20)
                    entry.grid(row=index + 1, column=col)
                    row.append(entry)
            self.entries.append(row)
        self.latest_index = 1

    def move_right(self, event):
        """Evento que hace que se seleccione la celda de la derecha
        al presionar la flecha de la derecha"""
        focus = self.parent_window.focus_get()
        index = 0
        for row in self.entries:
            for col in range(len(row)):
                e = self.entries[index][col]
                if e == focus and col not in [1, 6]:
                    try:
                        if col == 0:
                            self.entries[index][col + 2].focus_set()
                        elif col not in [5,6]:
                            self.entries[index][col + 1].focus_set()
                    except IndexError:
                        pass
            index = index + 1

    def move_left(self, event):
        """Evento que hace que se seleccione la celda de la izquierda
        al presionar la flecha de la izquierda"""
        focus = self.parent_window.focus_get()
        index = 0
        for row in self.entries:
            for col in range(len(row)):
                e = self.entries[index][col]
                if e == focus:
                    try:
                        if col == 2:
                            self.entries[index][col-2].focus_set()
                        elif col != 0:
                            self.entries[index][col-1].focus_set()
                    except IndexError:
                        pass
            index = index + 1

    def move_down(self, event):
        """Evento que hace que se seleccione la celda de abajo
        al presionar la flecha de abajo"""
        focus = self.parent_window.focus_get()
        index = 0
        for row in self.entries:
            for col in range(len(row)):
                e = self.entries[index][col]
                if e == focus:
                    try:
                        self.entries[index+1][col].focus_set()
                    except IndexError:
                        pass
            index = index + 1

    def move_up(self, event):
        """Evento que hace que se seleccione la celda de arriba
        al presionar la flecha de arriba"""
        focus = self.parent_window.focus_get()
        index = 0
        for row in self.entries:
            for col in range(len(row)):
                e = self.entries[index][col]
                if e == focus:
                    try:
                        self.entries[index-1][col].focus_set()
                    except IndexError:
                        pass
            index = index + 1