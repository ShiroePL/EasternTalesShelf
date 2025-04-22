# Eastern Tales Shelf

<p align="center">
  <img src="app/static/main_page.png" alt="Eastern Tales Shelf Logo"/>
</p>

A personal platform for organizing and tracking Eastern novels and manga. Eastern Tales Shelf allows you to easily link to reading sources, check release statuses, and manage your collection with seamless integration and backups from AniList.

## 📚 Features

- **AniList Integration**: Synchronize your manga and novel collection with AniList
- **Customizable UI**: Personalize your reading experience with custom color themes
- **Reading Status Tracking**: Track what you're currently reading, planning to read, or have completed
- **Real-time Updates**: Get notifications when new chapters are available for your favorite titles
- **Source Linking**: Easily link to sources like Bato.to for convenient reading
- **Advanced Filtering**: Filter your collection by type (novel, manga, manhwa), status, country of origin, and more
- **Search Functionality**: Quickly find titles in your collection
- **Cover Image Downloads**: Automatically download and display cover images for your collection
- **User Authentication**: Secure login system to protect your collection
- **Mobile-Friendly Design**: Responsive interface that works on various devices

## ✨ UI and Animations

Eastern Tales Shelf features a rich, interactive user interface with various animations that enhance the user experience:

- **3D Card Effects**: Manga and novel cards use perspective transforms for a 3D look that rotates on hover
- **Animated Transitions**: Smooth fade-in and slide animations when displaying content
- **AOS (Animate on Scroll)**: Elements gracefully animate as you scroll through your collection
- **Interactive Heart Animation**: Click the favorite icon to trigger a particle burst animation with GSAP
- **Flowing Hearts Effect**: Visual feedback when interacting with favorites
- **Custom Color Themes**: Real-time color theme changes with smooth transitions
- **Notification System**: Sliding notifications panel with status updates
- **Responsive Sidebar**: Smooth animations when opening/closing the details sidebar
- **Hover Effects**: Enhanced visual feedback on interactive elements
- **Status Color Coding**: Visual distinction between reading statuses (reading, completed, planning, etc.)


## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/EasternTalesShelf.git
   cd EasternTalesShelf
   ```

2. Set up a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the application:
   TO DO


## 🌈 Customization

Eastern Tales Shelf allows you to customize various aspects of the interface:

- **Color Themes**: Change background, primary, secondary, text, and border colors using the color picker circles in the navigation bar

## 🔌 JavaScript Modules

The application is organized into several JavaScript modules that handle different aspects of functionality:

- **colorPicker.js**: Manages theme customization and color settings
- **notifications.js**: Handles the real-time notification system
- **RightsidebarAnimations.js**: Controls animations for the details sidebar
- **filters.js**: Manages filtering functionality for your collection
- **eventListeners.js**: Handles user interactions and events
- **aos_stuff.js**: Configures and manages the Animate on Scroll library
- **mangaDownloader.js**: Handles downloading and managing manga content
- **queueManager.js**: Manages the download queue and background tasks

## 🔒 Security

The application includes several security features:
- CSRF protection
- Secure session cookies
- Password hashing
- Content Security Policy
- XSS protection

## 📱 Screenshots

(Screenshots would be placed here)


## 📄 License

This project is licensed under the terms of the license included in the repository.

## 🙏 Acknowledgements

- AniList for providing the API
- Bootstrap for the UI components
- GSAP for the animation library
- AOS for the scroll animations
- Various open-source libraries that made this project possible

---

<p align="center">
  Made with ❤️ for fans of Eastern tales
</p>
