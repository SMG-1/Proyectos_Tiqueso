import tkinter as tk
from tkinter import ttk
import os
from win32api import GetSystemMetrics

bg_color = 'white'


def center_window(toplevel, screen_width, screen_height):
    """Funcion para centrar las ventanas."""
    toplevel.update_idletasks()

    size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
    x = screen_width / 2 - size[0] / 2
    y = screen_height / 2 - size[1] / 2

    toplevel.geometry("+%d+%d" % (x, y))


class Main:
    def __init__(self, master, path):
        # tkinter root
        self.master = master

        # window parameters
        self.master.title("Módulo para Detección de Órdenes Anómalas - COPROLAC")
        self.master.configure(background=bg_color)

        # screen width and height, and toplevel width and height
        self.screen_width = GetSystemMetrics(0)
        self.screen_height = GetSystemMetrics(1)
        self.width = self.screen_width / 2
        self.height = self.screen_height / 2

        # Paned Window that contains the tree view and a master frame
        self.main_paned = tk.PanedWindow(self.master,
                                         #width=self.width,
                                         #height=self.height,
                                         orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=1)

        # Listbox - Shows status of the program and relevant information for the user.
        self.list_box = tk.Listbox(self.master,
                                   bg=bg_color,
                                   width=150,
                                   height=20)
        self.main_paned.add(self.list_box)
        self.list_box.insert(tk.END, 'Hola')
        self.list_box.insert(tk.END, '42 anomalias encontradas.')

        # Frame - Contains Load, Execute and Export buttons
        self.config_frame = tk.Frame(self.master,
                                     bg=bg_color)
        self.main_paned.add(self.config_frame)

        # Button - Load files
        self.btn_load_files = tk.Button(self.config_frame,
                                        bg=bg_color,
                                        text='Cargar archivos')
        self.btn_load_files.pack(padx=5,
                                 pady=10)

        # Button - Search
        self.btn_search = tk.Button(self.config_frame,
                                    bg=bg_color,
                                    text='Buscar anomalías')
        self.btn_search.pack(padx=5,
                             pady=10)

        # Button - Export result
        self.btn_export = tk.Button(self.config_frame,
                                    bg=bg_color,
                                    text='Exportar resultado')
        self.btn_export.pack(padx=5,
                             pady=10)

        center_window(self.master, self.screen_width, self.screen_height)


if __name__ == '__main__':
    path = os.path.join(os.path.expanduser("~"), r'AppData\Roaming\Modulo_Anomalas')

    root = tk.Tk()
    Main(root, path)
    root.mainloop()
