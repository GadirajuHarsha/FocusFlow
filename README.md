FocusFlow: Visualizing and Understanding Attentional Patterns
1. Introduction & Objective
FocusFlow is a desktop application designed to provide users with deep insights into their visual attention and focus habits during on-screen work. In an era of constant digital distractions, understanding where our attention goes is the first step toward improving concentration and productivity.

The primary objective of this project was to move beyond simple gaze plotting and develop a tool that quantifies meaningful psychological metrics related to focus. By interfacing with webcam-based eye-tracking software, FocusFlow monitors a user’s gaze, processes it against user-defined work contexts, and presents the analysis through intuitive real-time cues and detailed post-session reports. It empowers users to answer critical questions: How much time do I truly spend on-task? How easily am I distracted? How quickly can I recover my focus?

2. The Psychology of Focus: Core Metrics Explained
The entire application is built around quantifying four key psychological indicators of attention.

Metric 1: Dwell Time
Concept: Selective attention is the act of focusing on a particular object for a certain period while ignoring irrelevant information. Sustained dwell time within a task-relevant area is a strong proxy for cognitive engagement.

Implementation: FocusFlow measures the total time and percentage of a session the user's gaze remains within "Productive" versus "Distraction" Areas of Interest (AOIs). This provides a high-level overview of how a session was spent.

Metric 2: Transition Frequency
Concept: Attentional control is the ability to voluntarily direct and maintain one's focus. Frequent, rapid shifts between productive and distracting areas can indicate poor attentional control, a fragmented attention span, or a state of active self-interruption.

Implementation: The application counts the number of times gaze shifts directly from a "Productive" AOI to a "Distraction" one, and vice-versa. A high count suggests a "choppy" and inefficient work pattern.

Metric 3: Focus Bout Analysis
Concept: True productivity isn't just about total time on task, but about achieving periods of sustained attention, or "deep work." A "focus bout" represents an uninterrupted period of concentration. Crucially, a momentary glance away should not be considered a break in focus.

Implementation: FocusFlow identifies continuous periods where gaze remains within a "Productive" AOI. A bout is only considered "broken" if the user's gaze moves to a "Distraction" AOI and remains there for a significant duration (defaulting to >3 seconds). This nuanced approach avoids penalizing the user for brief, natural eye movements, providing a more realistic measure of deep work. The report calculates the total number of bouts, the average duration, and the longest single bout.

Metric 4: Re-engagement Latency
Concept: Cognitive flexibility and the "cost of distraction" can be measured by how quickly one can return to a task after being pulled away. A long latency period indicates that a distraction had a significant lingering impact, making it difficult to re-establish a productive mindset.

Implementation: The application first identifies "significant distractions" (where dwell time in a "Distraction" AOI exceeds a threshold of >3 seconds). It then measures the time elapsed from the end of that significant distraction until the gaze first returns to a "Productive" AOI. The report provides the average latency across all such instances in a session.

3. Functionality & Features
FocusFlow is designed with a clean, user-centric workflow, from initial setup to final analysis.

Modern Themed Interface: Utilizes the external "Azure" ttk theme for a sleek, modern look and feel, with support for both light and dark modes.

Landing Page: A welcoming home screen featuring the application logo and a brief introduction.

Transparent Fullscreen AOI Definition: A highly intuitive method for defining Areas of Interest. The main window fades, and a semi-transparent overlay covers the entire screen, allowing the user to draw rectangles directly over their actual applications and windows. Previously defined AOIs remain visible for reference.

Real-time Session Overlay: During an active session, the main window is hidden and replaced by a small, unobtrusive overlay that is always on top. This overlay displays:

A running session timer.

A real-time focus indicator, a colored circle that dynamically changes based on time-aware rules (e.g., deep green for sustained focus, bright red for significant distraction, yellow for frequent task-switching).

An "End Session" button.

Comprehensive Report Window: After a session, a maximized window appears with a detailed, scrollable report.

Rich Text Metrics: A clear, formatted summary of all calculated metrics using bolding and indentation for readability.

Matplotlib Visualizations:

A Dwell Time Pie Chart showing the percentage breakdown of time spent in Productive, Distraction, and Outside areas.

An Attention Timeline Graph that plots the user's focus state over the entire session duration, providing an at-a-glance view of the session's rhythm.

Data Export: A "Save Report" button that saves the complete session data (including the raw gaze log and all calculated metrics) to a JSON file.

Report Comparison: A "View Saved Reports" button on the main screen and an "Open & Compare" button in the report window allow a user to load a previously saved session and view it side-by-side with the current one for progress tracking.

4. The Development Process: An Iterative Journey
The creation of FocusFlow followed an iterative and user-experience-focused development process.

Foundation: The project began with a single-window Tkinter application that established the core functionality: connecting to the GazeFlowClient, reading gaze data, and performing basic calculations printed to the console.

Structural Refactoring: Recognizing the need for a better user flow, the application was refactored into a multi-page design using different ttk.Frame instances for a landing page and the main application controls.

UI Modernization: To move beyond the classic Tkinter look, ttk themed widgets were implemented. When this was still not sufficient, the project was adapted to use the external Azure theme, which required sourcing .tcl files and modifying the application to leverage the theme's custom styles (like Card.TFrame and Accent.TButton).

Intuitive AOI Definition: The initial method of defining AOIs on a small canvas was replaced with the significantly more intuitive transparent fullscreen overlay. This involved managing Toplevel windows, their alpha (transparency) attributes, and mapping screen coordinates back to the application's internal logic.

Enhanced Reporting: The simple console output was replaced by a sophisticated report generation system. This involved creating a new, scrollable Toplevel window and integrating Matplotlib charts by embedding FigureCanvasTkAgg canvases directly into the Tkinter UI. Logic for saving/loading session data via JSON and displaying reports side-by-side was also added.

Logic Refinement & Debugging: The final and most complex stage involved implementing the nuanced psychological metrics. The logic for Focus Bouts and Re-engagement Latency was built, and the real-time indicator was upgraded from a simple instantaneous status display to a stateful system aware of time and transition frequency. This stage involved significant debugging to ensure the calculations were accurate and the real-time feedback was responsive and correct.

5. Tech Stack
Backend & Core Logic: Python 3

GUI: Tkinter, using the ttk themed widgets for a modern foundation.

GUI Theming: The external Azure-ttk-theme by rdbende, loaded via its .tcl script.

Data Visualization: Matplotlib, embedded within the Tkinter application.

Numerical Operations: NumPy (used by Matplotlib).

Image Handling: Pillow (PIL) for displaying the application logo.

Eye-Tracking Interface: A custom gaze_client.py designed to connect to and parse data from the GazeFlowAPI.

AOI Definition: Handled via Tkinter's native event binding on Toplevel and Canvas widgets (superseding the initial plan to use pynput).

6. Future Functionality
While the current version of FocusFlow is a complete and functional tool, the following enhancements could be made to further increase its utility:

More Nuanced AOI Categories: The biggest planned improvement is to move beyond the simple "Productive" vs. "Distraction" dichotomy. Future versions could allow users to define more granular categories, such as:

Primary Task: The main window or document being worked on.

Reference Material: Documentation, web pages for research, etc.

Task-Related Communication: Slack, Teams, or email windows.

Distraction: Social media, news sites, etc.
This would enable much richer metrics, such as "Time spent referencing material while in a productive bout" or "Frequency of switching from task to communication."

Configuration Screen: Add a settings page within the UI to allow users to input the host/port for the eye-tracking software and adjust the time thresholds used for metric calculations (e.g., change the "significant distraction" time from 3s to 5s).

Historical Analysis: Implement a view to see trends over multiple saved reports, such as plotting the average focus bout duration over the last 7 days.

Sound Cues: Add optional, subtle sound cues to accompany the visual focus indicator to provide non-visual feedback.