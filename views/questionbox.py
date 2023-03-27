import tkinter as tk
from tkinter import ttk


class PopupQuestion:
    """
    Simple popup box to ask a question with two possible answers.
    Two possible answers can be specified.
    Once the popup is closed, callback is called with the answer as parameter.

    Parameters
    ----------
    callback: function with one input parameter
        Called if any answer is chosen.
        True if left button is pressed, False if right button is pressed.
    title : str
        Title of the popup window.
    question : str
        Main text of the popup window.
    answer_true : str
        Caption of the left button.
        The method returns True if this button is pressed.
    answer_false : str
        Caption of the left button.
        The method returns True if this button is pressed.
    """

    def __init__(self, callback, title, question, answer_true, answer_false):
        """
        Parameters
        ----------
        callback : function
            A function to be called with the user's answer as a boolean argument.
        title : str
            The title of the popup window.
        question : str
            The question to display in the popup window.
        answer_true : str
            The label for the 'True' button.
        answer_false : str
            The label for the 'False' button.
        """
        # Create a new window object
        self.popup = tk.Toplevel()
        # Assign a title to it
        self.popup.title(title)
        # Set the protocol for the window to call the 'true_pressed' method when the 'x' button is clicked
        self.popup.protocol("WM_DELETE_WINDOW", self.true_pressed)
        self.callback = callback
        self.answer = None
        # Add the question as a label to the top of the window
        label = ttk.Label(self.popup, text=question, width=60, wraplength=340)
        label.pack(side="top", fill="x", pady=10)
        # Add a button for the 'True' answer to the left of the window
        BT = ttk.Button(self.popup, text=answer_true, command=self.true_pressed)
        BT.pack(side="left", padx=10, pady=10)
        # Add a button for the 'False' answer to the bottom of the window
        BF = ttk.Button(self.popup, text=answer_false, command=self.false_pressed)
        BF.pack(side="bottom", padx=10, pady=10)
        # Add a button for cancelling the window to the right of the window
        BC = ttk.Button(self.popup, text='Cancel', command=self.cancelled)
        BC.pack(side="right", padx=10, pady=10)
        # Start the mainloop for the popup window
        self.popup.mainloop()

    def true_pressed(self):
        """
        Called when the 'True' button is pressed.
        Destroys the popup window and calls the callback with a value of True.
        """
        self.popup.destroy()
        self.callback(True)

    def false_pressed(self):
        """
        Called when the 'False' button is pressed.
        Destroys the popup window and calls the callback with a value of False.
        """
        self.popup.destroy()
        self.callback(False)

    def cancelled(self):
        """
        Called when the 'Cancel' button is pressed.
        Destroys the popup window.
        """
        self.popup.destroy()
