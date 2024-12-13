import sys
import os
import subprocess
import re
from PyQt5 import QtWidgets, QtGui, QtCore
import fitz  # PyMuPDF
import platform

class BookWidget(QtWidgets.QWidget):
    """Custom widget to display a PDF thumbnail, title, and handle selection and opening."""
    
    # Define a custom signal to notify selection changes
    selection_changed_signal = QtCore.pyqtSignal()
    
    def __init__(self, pdf_path, thumbnail_size=(120, 180), parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.thumbnail_size = thumbnail_size
        self.selected = False  # Track selection state
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Thumbnail
        self.thumbnail_label = QtWidgets.QLabel()
        self.thumbnail_label.setFixedSize(*self.thumbnail_size)
        self.thumbnail_label.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = self.get_thumbnail()
        if pixmap:
            self.thumbnail_label.setPixmap(pixmap.scaled(
                self.thumbnail_size[0],
                self.thumbnail_size[1],
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            ))
        else:
            # Default icon if thumbnail generation fails
            default_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
            self.thumbnail_label.setPixmap(default_icon.pixmap(*self.thumbnail_size))

        layout.addWidget(self.thumbnail_label)

        # Book Name
        self.name_label = QtWidgets.QLabel(os.path.basename(self.pdf_path))
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.name_label.setFixedWidth(self.thumbnail_size[0])
        self.name_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Maximum)
        layout.addWidget(self.name_label)

        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())  # Ensure the widget has a fixed size

        # Set default background
        self.update_background()

    def get_thumbnail(self):
        """Generate a thumbnail image for the first page of the PDF."""
        try:
            doc = fitz.open(self.pdf_path)
            if doc.page_count < 1:
                return None
            page = doc.load_page(0)  # Load first page
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Higher resolution
            image = QtGui.QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QtGui.QImage.Format_RGBA8888 if pix.alpha else QtGui.QImage.Format_RGB888
            )
            return QtGui.QPixmap.fromImage(image)
        except Exception as e:
            print(f"Failed to generate thumbnail for {self.pdf_path}: {e}")
            return None

    def mousePressEvent(self, event):
        """Handle mouse press events for selection."""
        if event.button() == QtCore.Qt.LeftButton:
            self.toggle_selection()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle mouse double-click events to open the PDF."""
        if event.button() == QtCore.Qt.LeftButton:
            self.open_pdf()
        super().mouseDoubleClickEvent(event)

    def toggle_selection(self):
        """Toggle the selection state and update background."""
        self.selected = not self.selected
        self.update_background()
        # Emit a custom signal to notify selection change
        self.selection_changed_signal.emit()

    def select_all(self, select=True):
        """Set the selection state."""
        self.selected = select
        self.update_background()

    def update_background(self):
        """Update the background color based on selection."""
        if self.selected:
            self.setStyleSheet("background-color: lightblue; border: 1px solid blue;")
        else:
            self.setStyleSheet("background-color: none; border: none;")

    def open_pdf(self):
        """Open the PDF using the system's default viewer."""
        try:
            if platform.system() == "Windows":
                os.startfile(self.pdf_path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", self.pdf_path])
            else:
                subprocess.call(["xdg-open", self.pdf_path])
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to open the PDF file.\nError: {e}"
            )

class OutputWindow(QtWidgets.QDockWidget):
    """Dockable window to display script output and progress."""

    def __init__(self, parent=None):
        super().__init__("Processing Output", parent)
        self.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea | QtCore.Qt.TopDockWidgetArea)

        # Main widget
        main_widget = QtWidgets.QWidget()
        self.setWidget(main_widget)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        main_widget.setLayout(layout)

        # Progress Bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Output Text Editor
        self.output_editor = QtWidgets.QPlainTextEdit()
        self.output_editor.setReadOnly(True)
        self.output_editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: black;
                color: #00FF00;
                font-family: 'Courier New';
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.output_editor)

        # Set fixed height for the output window
        self.setFixedHeight(300)

class SemanticTreeTab(QtWidgets.QWidget):
    """Placeholder widget for the Semantic Tree tab."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        
        # Placeholder content
        label = QtWidgets.QLabel("Semantic Tree will be displayed here.")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        
        # You can add more widgets related to Semantic Tree visualization here
        # For example, a QTreeView or a custom widget for rendering the tree

class PdfBookViewer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Book Viewer")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize UI components
        self.init_ui()

        # Load PDF files
        self.load_pdf_files()

    def init_ui(self):
        # Create Menu Bar
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")
        open_action = QtWidgets.QAction("&Open Directory", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_directory)
        file_menu.addAction(open_action)

        exit_action = QtWidgets.QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(QtWidgets.qApp.quit)
        file_menu.addAction(exit_action)

        # About Menu
        about_menu = menubar.addMenu("&About")
        about_action = QtWidgets.QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        about_menu.addAction(about_action)

        # Create Status Bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Add "Selected X of Y" label to the status bar
        self.selection_label = QtWidgets.QLabel("0 selected of 0")
        self.status_bar.addPermanentWidget(self.selection_label)

        # Add "Stop" button to the status bar
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setToolTip("Stop the Semantize Process")
        self.stop_button.setFixedHeight(40)  # Make the button bigger
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: red;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
        self.stop_button.setEnabled(False)  # Initially disabled
        self.status_bar.addPermanentWidget(self.stop_button)
        self.stop_button.clicked.connect(self.stop_semantize)

        # Add "Semantize" button to the status bar
        self.semantize_button = QtWidgets.QPushButton("Semantize")
        self.semantize_button.setToolTip("Execute Semantize Process")
        self.semantize_button.setFixedHeight(40)  # Make the button bigger
        self.semantize_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.status_bar.addPermanentWidget(self.semantize_button)
        self.semantize_button.clicked.connect(self.run_semantize)

        # Add Theme Toggle Button to the Status Bar
        self.theme_toggle_button = QtWidgets.QPushButton("Switch to Dark Theme")
        self.theme_toggle_button.setToolTip("Toggle between Dark and Light Themes")
        self.theme_toggle_button.setFixedHeight(40)
        self.theme_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        self.status_bar.addPermanentWidget(self.theme_toggle_button)
        self.theme_toggle_button.clicked.connect(self.toggle_theme)

        # Create central widget with QTabWidget
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create "PDF Processing" tab
        self.pdf_processing_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.pdf_processing_tab, "PDF Processing")
        self.init_pdf_processing_tab()

        # Create "Semantic Tree" tab
        self.semantic_tree_tab = SemanticTreeTab()
        self.tabs.addTab(self.semantic_tree_tab, "Semantic Tree")

        # Initialize Output Window
        self.output_window = OutputWindow(self)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.output_window)

        # Initialize QProcess
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        # Initialize Theme
        self.dark_theme = False  # Start with Light Theme
        self.apply_light_theme()

    def init_pdf_processing_tab(self):
        """Initialize the PDF Processing tab with Select All button and PDF grid."""
        layout = QtWidgets.QVBoxLayout()
        self.pdf_processing_tab.setLayout(layout)

        # Add "Select All" button at the top
        self.select_all_button = QtWidgets.QPushButton("Select All")
        self.select_all_button.setToolTip("Select or Deselect All PDFs")
        self.select_all_button.setFixedHeight(40)  # Make the button bigger
        self.select_all_button.setStyleSheet("""
            QPushButton {
                background-color: #008CBA;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #007B9E;
            }
        """)
        self.select_all_button.clicked.connect(self.select_all_pdfs)
        layout.addWidget(self.select_all_button)

        # Add scroll area for PDF grid
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

        # Container widget inside scroll area
        self.container = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.container)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(20)

        self.scroll_area.setWidget(self.container)

    def open_directory(self):
        """Open a dialog to select the root directory containing PDF books."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select PDF Directory", "", QtWidgets.QFileDialog.ShowDirsOnly
        )
        if directory:
            self.pdf_directory = directory
            self.load_pdf_files()

    def show_about(self):
        """Display the About dialog."""
        QtWidgets.QMessageBox.about(
            self,
            "About PDF Book Viewer",
            "<b>PDF Book Viewer</b><br>"
            "A simple tool to view and process PDF books with thumbnails arranged in a grid.<br>"
            "Developed using PyQt5 and PyMuPDF.",
        )

    def load_pdf_files(self):
        """Recursively scan the root directory for PDF files and display them."""
        # Set default root directory
        default_root = "/brainboost/brainboost_data/data_tools/brainboost_datatools_subjective_semantizer/com_worktwins_data/books_pdf"

        # Use default root if not already set
        if not hasattr(self, 'pdf_directory') or not self.pdf_directory:
            self.pdf_directory = default_root

        if not os.path.exists(self.pdf_directory):
            QtWidgets.QMessageBox.critical(
                self, "Error", f"The directory {self.pdf_directory} does not exist."
            )
            self.status_bar.showMessage("Directory does not exist.")
            return

        # Clear existing items
        # Remove all widgets from the grid layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        # Recursively get list of PDF files
        pdf_files = []
        for root, dirs, files in os.walk(self.pdf_directory):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))

        if not pdf_files:
            self.status_bar.showMessage("No PDF files found in the directory.")
            return

        self.status_bar.showMessage(f"Loading {len(pdf_files)} PDF files...")

        self.book_widgets = []  # Store book widgets for resizing
        for pdf_path in pdf_files:
            book_widget = BookWidget(pdf_path)
            book_widget.selection_changed_signal.connect(self.selection_changed)
            self.book_widgets.append(book_widget)

        # Arrange widgets in the grid
        self.arrange_widgets_in_grid()

        # Update the selection label
        self.update_selection_label()

        self.status_bar.showMessage(f"Loaded {len(pdf_files)} PDF files.")

    def arrange_widgets_in_grid(self):
        """Arrange the BookWidgets in a grid layout."""
        # Clear existing items
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        if not self.book_widgets:
            return

        # Calculate the number of columns based on the window width
        available_width = self.scroll_area.viewport().width()
        if not self.book_widgets:
            return
        widget_width = self.book_widgets[0].width() + self.grid_layout.spacing()
        columns = max(1, available_width // widget_width)

        # Arrange widgets
        for index, widget in enumerate(self.book_widgets):
            row = index // columns
            col = index % columns
            self.grid_layout.addWidget(widget, row, col)

    def resizeEvent(self, event):
        """Handle window resize to adjust the grid layout."""
        super().resizeEvent(event)
        # Only rearrange if in the PDF Processing tab
        if self.tabs.currentWidget() == self.pdf_processing_tab:
            self.arrange_widgets_in_grid()

    def select_all_pdfs(self):
        """Select or Deselect all PDFs based on current selection."""
        if all(widget.selected for widget in self.book_widgets):
            # All are selected; deselect all
            for widget in self.book_widgets:
                widget.select_all(False)
            self.select_all_button.setText("Select All")
        else:
            # Select all
            for widget in self.book_widgets:
                widget.select_all(True)
            self.select_all_button.setText("Deselect All")
        # Update the selection label
        self.update_selection_label()

    def selection_changed(self):
        """Update the selection label when a selection changes."""
        self.update_selection_label()

    def update_selection_label(self):
        """Update the 'X selected of Y' label in the status bar."""
        selected = sum(widget.selected for widget in self.book_widgets)
        total = len(self.book_widgets)
        self.selection_label.setText(f"{selected} selected of {total}")

    def run_semantize(self):
        """Execute the main.py script and display output."""
        # Collect selected PDF files
        selected_pdfs = [widget.pdf_path for widget in self.book_widgets if widget.selected]

        if not selected_pdfs:
            QtWidgets.QMessageBox.warning(
                self, "No Selection", "Please select at least one PDF file to semantize."
            )
            return

        # Path to the script
        script_path = os.path.join(os.getcwd(), "main.py")

        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.critical(
                self, "Error", f"The script {script_path} does not exist."
            )
            return

        # Path to the Python executable in 'myenv'
        if platform.system() == "Windows":
            python_executable = os.path.join(os.getcwd(), "myenv", "Scripts", "python.exe")
        else:
            python_executable = os.path.join(os.getcwd(), "myenv", "bin", "python3")

        if not os.path.exists(python_executable):
            QtWidgets.QMessageBox.critical(
                self, "Error",
                f"The Python executable was not found in the 'myenv' environment.\nExpected at: {python_executable}"
            )
            return

        # Disable the "Semantize" button and enable the "Stop" button
        self.semantize_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Clear previous output
        self.output_window.output_editor.clear()
        self.output_window.progress_bar.setValue(0)

        # Prepare the command with selected PDF paths
        # Pass the script path and selected PDFs as arguments with '-f'
        arguments = [script_path, '-f'] + selected_pdfs

        # Start the process
        self.process.start(python_executable, arguments)

        if not self.process.waitForStarted(1000):
            QtWidgets.QMessageBox.critical(
                self, "Error", "Failed to start the Semantize process."
            )
            self.semantize_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def stop_semantize(self):
        """Terminate the running Semantize process."""
        if self.process.state() == QtCore.QProcess.Running:
            self.process.kill()
            self.output_window.output_editor.appendPlainText("\nProcess Terminated by User.")
            self.output_window.progress_bar.setValue(0)
            self.semantize_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def handle_stdout(self):
        """Handle standard output from the process."""
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.output_window.output_editor.appendPlainText(stdout)

        # Attempt to parse progress information
        progress = self.extract_progress(stdout)
        if progress is not None:
            self.output_window.progress_bar.setValue(progress)

    def handle_stderr(self):
        """Handle standard error from the process."""
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.output_window.output_editor.appendPlainText(stderr)

    def process_finished(self):
        """Handle process completion."""
        self.output_window.output_editor.appendPlainText("\nProcess Finished.")
        self.output_window.progress_bar.setValue(100)
        self.semantize_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def extract_progress(self, text):
        """
        Extract progress percentage from the output text.
        Assumes that the script outputs lines containing 'Progress: X%' where X is an integer.
        """
        match = re.search(r'Progress:\s*(\d+)%', text)
        if match:
            return int(match.group(1))
        return None

    def toggle_theme(self):
        """Toggle between Dark and Light Themes."""
        self.dark_theme = not self.dark_theme
        if self.dark_theme:
            self.apply_dark_theme()
            self.theme_toggle_button.setText("Switch to Light Theme")
        else:
            self.apply_light_theme()
            self.theme_toggle_button.setText("Switch to Dark Theme")

    def apply_dark_theme(self):
        """Apply Dark Theme styles."""
        dark_stylesheet = """
            QWidget {
                background-color: #2b2b2b;
                color: #f0f0f0;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #f0f0f0;
                border: 1px solid #555555;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QScrollArea {
                background-color: #2b2b2b;
            }
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #00FF00;
            }
            QProgressBar {
                background-color: #3c3c3c;
                color: #00FF00;
                border: 1px solid #555555;
            }
            QProgressBar::chunk {
                background-color: #00FF00;
            }
            QLabel {
                color: #f0f0f0;
            }
            QTabWidget::pane { /* The tab widget frame */
                border-top: 2px solid #C2C7CB;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #C4C4C3;
                padding: 10px;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #FFFFFF;
            }
        """
        self.setStyleSheet(dark_stylesheet)

    def apply_light_theme(self):
        """Apply Light Theme styles."""
        light_stylesheet = """
            QWidget {
                background-color: #ffffff;
                color: #000000;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #a0a0a0;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QScrollArea {
                background-color: #ffffff;
            }
            QPlainTextEdit {
                background-color: #f5f5f5;
                color: #000000;
            }
            QProgressBar {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #a0a0a0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
            QLabel {
                color: #000000;
            }
            QTabWidget::pane { /* The tab widget frame */
                border-top: 2px solid #C2C7CB;
            }
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #C4C4C3;
                padding: 10px;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #FFFFFF;
            }
        """
        self.setStyleSheet(light_stylesheet)

class SemanticTreeTab(QtWidgets.QWidget):
    """Placeholder widget for the Semantic Tree tab."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        
        # Placeholder content
        label = QtWidgets.QLabel("Semantic Tree will be displayed here.")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        
        # You can add more widgets related to Semantic Tree visualization here
        # For example, a QTreeView or a custom widget for rendering the tree

def main():
    app = QtWidgets.QApplication(sys.argv)
    viewer = PdfBookViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
