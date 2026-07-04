import warnings
import tkinter as tk

warnings.filterwarnings("ignore", category=UserWarning, module="pycaw.utils")

from gui import ToneGenApp


def main():
    root = tk.Tk()
    ToneGenApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
