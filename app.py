import React, { useState, useEffect, createContext, useContext } from 'react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from 'firebase/auth';
import { getFirestore, doc, getDoc, addDoc, setDoc, updateDoc, deleteDoc, onSnapshot, collection, query, where, getDocs } from 'firebase/firestore';

// --- Firebase Context ---
const FirebaseContext = createContext(null);

// Firebase Provider component to initialize Firebase and manage auth state
const FirebaseProvider = ({ children }) => {
  const [db, setDb] = useState(null);
  const [auth, setAuth] = useState(null);
  const [userId, setUserId] = useState(null);
  const [loadingFirebase, setLoadingFirebase] = useState(true);

  useEffect(() => {
    // Initialize Firebase
    let app;
    let firestoreDb;
    let firebaseAuth;

    try {
      // Access global __firebase_config and __app_id
      const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
      const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : {};

      if (Object.keys(firebaseConfig).length > 0) {
        app = initializeApp(firebaseConfig);
        firestoreDb = getFirestore(app);
        firebaseAuth = getAuth(app);
        setDb(firestoreDb);
        setAuth(firebaseAuth);

        // Sign in anonymously or with custom token
        const signIn = async () => {
          try {
            if (typeof __initial_auth_token !== 'undefined') {
              await signInWithCustomToken(firebaseAuth, __initial_auth_token);
            } else {
              await signInAnonymously(firebaseAuth);
            }
          } catch (error) {
            console.error("Firebase authentication error:", error);
          } finally {
            setLoadingFirebase(false);
          }
        };

        // Listen for auth state changes
        const unsubscribe = onAuthStateChanged(firebaseAuth, (user) => {
          if (user) {
            setUserId(user.uid);
          } else {
            setUserId(crypto.randomUUID()); // Anonymous or unauthenticated user ID
          }
          if (loadingFirebase) { // Only set loading to false after the first auth state check
            setLoadingFirebase(false);
          }
        });

        signIn(); // Call sign-in function
        return () => unsubscribe(); // Cleanup auth listener
      } else {
        console.warn("Firebase config not found. App will run without Firebase services.");
        setLoadingFirebase(false);
      }
    } catch (error) {
      console.error("Error initializing Firebase:", error);
      setLoadingFirebase(false);
    }
  }, []);

  return (
    <FirebaseContext.Provider value={{ db, auth, userId, loadingFirebase }}>
      {children}
    </FirebaseContext.Provider>
  );
};

// --- Icons (Lucide React) ---
// Using inline SVG for simplicity as lucide-react needs direct import
// For a full app, you'd install and import from 'lucide-react'
const HomeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-home">
    <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    <polyline points="9 22 9 12 15 12 15 22" />
  </svg>
);

const BoxIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-box">
    <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
    <path d="m3.3 7 8.7 5 8.7-5" />
    <path d="M12 22V12" />
  </svg>
);

const FolderIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-folder">
    <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
  </svg>
);

const PlusCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-plus-circle">
    <circle cx="12" cy="12" r="10" />
    <path d="M8 12h8" />
    <path d="M12 8v8" />
  </svg>
);

const XIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-x">
    <path d="M18 6 6 18" />
    <path d="m6 6 12 12" />
  </svg>
);

// --- Components ---

// Modal component for alerts and confirmations
const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-sm">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-gray-800">{title}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <XIcon />
          </button>
        </div>
        <div className="text-gray-700 mb-4">{children}</div>
        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-150 ease-in-out"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};


// Deal Card Component
const DealCard = ({ deal }) => (
  <div className="bg-white rounded-xl shadow-md overflow-hidden transform transition duration-300 hover:scale-105 border border-gray-200">
    <img
      src={deal.imageUrl || `https://placehold.co/400x200/e0e7ff/4338ca?text=CraftGrab`}
      alt={deal.title}
      className="w-full h-48 object-cover"
      onError={(e) => { e.target.onerror = null; e.target.src = `https://placehold.co/400x200/e0e7ff/4338ca?text=CraftGrab` }}
    />
    <div className="p-4">
      <h3 className="font-semibold text-lg text-gray-800 mb-1">{deal.title}</h3>
      <p className="text-indigo-600 font-bold text-xl mb-2">{deal.price}</p>
      <p className="text-sm text-gray-600 mb-2">{deal.shop}</p>
      <div className="flex flex-wrap gap-2">
        {deal.tags.map((tag, index) => (
          <span key={index} className="bg-indigo-100 text-indigo-700 text-xs px-2 py-1 rounded-full font-medium">
            {tag}
          </span>
        ))}
      </div>
    </div>
  </div>
);

// Home Feed Screen
const HomeFeed = () => {
  const deals = [
    {
      id: 1,
      title: "Super Soft Merino Yarn",
      price: "$9.99/skein",
      shop: "Yarn Haven",
      tags: ["Merino", "Worsted", "Sale"],
      imageUrl: "https://placehold.co/400x200/e0e7ff/4338ca?text=Merino+Yarn",
    },
    {
      id: 2,
      title: "Cotton Blend Fabric Bundle",
      price: "$24.99",
      shop: "Fabric Emporium",
      tags: ["Fabric", "Quilting", "Bundle"],
      imageUrl: "https://placehold.co/400x200/e0e7ff/4338ca?text=Fabric+Bundle",
    },
    {
      id: 3,
      title: "Knitting Needle Set - 50% Off",
      price: "$19.99",
      shop: "Crafty Supplies",
      tags: ["Needles", "Tools", "Discount"],
      imageUrl: "https://placehold.co/400x200/e0e7ff/4338ca?text=Knitting+Needles",
    },
    {
      id: 4,
      title: "Alpaca Silk Fingering Yarn",
      price: "$14.50/skein",
      shop: "The Fiber Nook",
      tags: ["Alpaca", "Silk", "Fingering"],
      imageUrl: "https://placehold.co/400x200/e0e7ff/4338ca?text=Alpaca+Silk",
    },
    {
      id: 5,
      title: "Crochet Hook Set",
      price: "$12.00",
      shop: "Joann Fabrics",
      tags: ["Crochet", "Tools", "New"],
      imageUrl: "https://placehold.co/400x200/e0e7ff/4338ca?text=Crochet+Hooks",
    },
  ];

  return (
    <div className="p-4 sm:p-6 bg-gray-50 min-h-screen">
      <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center sm:text-left">Featured Deals</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {deals.map((deal) => (
          <DealCard key={deal.id} deal={deal} />
        ))}
      </div>
    </div>
  );
};

// Stash Organizer Screen
const StashOrganizer = () => {
  const [stash, setStash] = useState([
    { id: 1, name: "Merino Worsted - Blue", fiber: "Merino Wool", weight: "Worsted", yardage: "200 yards", skeins: 3, color: "#80BFFF" },
    { id: 2, name: "Cotton DK - Green", fiber: "Cotton", weight: "DK", yardage: "250 yards", skeins: 2, color: "#82E0AA" },
    { id: 3, name: "Alpaca Lace - Grey", fiber: "Alpaca", weight: "Lace", yardage: "400 yards", skeins: 1, color: "#C0C0C0" },
  ]);

  const [isAddingYarn, setIsAddingYarn] = useState(false);
  const [newYarn, setNewYarn] = useState({ name: '', fiber: '', weight: '', yardage: '', skeins: '', color: '#CCCCCC' });

  const handleAddYarn = (e) => {
    e.preventDefault();
    if (!newYarn.name) {
      alert("Yarn name is required."); // Replaced with Modal in next iteration
      return;
    }
    setStash([...stash, { ...newYarn, id: stash.length + 1 }]);
    setNewYarn({ name: '', fiber: '', weight: '', yardage: '', skeins: '', color: '#CCCCCC' });
    setIsAddingYarn(false);
  };

  return (
    <div className="p-4 sm:p-6 bg-gray-50 min-h-screen">
      <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center sm:text-left">My Stash</h2>

      <button
        onClick={() => setIsAddingYarn(true)}
        className="flex items-center justify-center px-4 py-2 mb-6 bg-indigo-600 text-white rounded-lg shadow-md hover:bg-indigo-700 transition duration-150 ease-in-out w-full sm:w-auto"
      >
        <PlusCircleIcon className="mr-2" /> Add New Yarn
      </button>

      <Modal isOpen={isAddingYarn} onClose={() => setIsAddingYarn(false)} title="Add New Yarn to Stash">
        <form onSubmit={handleAddYarn} className="space-y-4">
          <div>
            <label htmlFor="yarnName" className="block text-sm font-medium text-gray-700">Yarn Name</label>
            <input
              type="text"
              id="yarnName"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              value={newYarn.name}
              onChange={(e) => setNewYarn({ ...newYarn, name: e.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="fiber" className="block text-sm font-medium text-gray-700">Fiber Type</label>
            <input
              type="text"
              id="fiber"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              value={newYarn.fiber}
              onChange={(e) => setNewYarn({ ...newYarn, fiber: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="weight" className="block text-sm font-medium text-gray-700">Weight</label>
            <select
              id="weight"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              value={newYarn.weight}
              onChange={(e) => setNewYarn({ ...newYarn, weight: e.target.value })}
            >
              <option value="">Select Weight</option>
              <option value="Lace">Lace</option>
              <option value="Fingering">Fingering</option>
              <option value="Sport">Sport</option>
              <option value="DK">DK</option>
              <option value="Worsted">Worsted</option>
              <option value="Aran">Aran</option>
              <option value="Bulky">Bulky</option>
              <option value="Super Bulky">Super Bulky</option>
            </select>
          </div>
          <div>
            <label htmlFor="yardage" className="block text-sm font-medium text-gray-700">Yardage</label>
            <input
              type="text"
              id="yardage"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              value={newYarn.yardage}
              onChange={(e) => setNewYarn({ ...newYarn, yardage: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="skeins" className="block text-sm font-medium text-gray-700">Skeins</label>
            <input
              type="number"
              id="skeins"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              value={newYarn.skeins}
              onChange={(e) => setNewYarn({ ...newYarn, skeins: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="color" className="block text-sm font-medium text-gray-700">Color (Hex or Name)</label>
            <input
              type="color"
              id="color"
              className="mt-1 block w-full h-10 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              value={newYarn.color}
              onChange={(e) => setNewYarn({ ...newYarn, color: e.target.value })}
            />
          </div>
          <button
            type="submit"
            className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-150 ease-in-out"
          >
            Add Yarn
          </button>
        </form>
      </Modal>

      {stash.length === 0 ? (
        <p className="text-gray-600 text-center py-8">No yarn in your stash yet! Click "Add New Yarn" to get started.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {stash.map((yarn) => (
            <div key={yarn.id} className="bg-white rounded-xl shadow-md p-4 flex items-center space-x-4 border border-gray-200">
              <div
                className="w-16 h-16 rounded-full flex-shrink-0"
                style={{ backgroundColor: yarn.color || '#CCCCCC', border: '1px solid #ddd' }}
                title={`Color: ${yarn.color}`}
              ></div>
              <div>
                <h3 className="font-semibold text-lg text-gray-800">{yarn.name}</h3>
                <p className="text-sm text-gray-600">
                  {yarn.fiber} &bull; {yarn.weight} &bull; {yarn.yardage} &bull; {yarn.skeins} skeins
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Project Organizer Screen
const ProjectOrganizer = () => {
  const [projects, setProjects] = useState([
    { id: 1, name: "Cozy Winter Scarf", pattern: "Simple Ribbed Scarf Pattern", yarnUsed: "Merino Worsted - Blue (2 skeins)", status: "In Progress" },
    { id: 2, name: "Baby Blanket", pattern: "Cuddly Baby Blanket", yarnUsed: "Cotton DK - Green (1 skein)", status: "Completed" },
  ]);

  const [isAddingProject, setIsAddingProject] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', pattern: '', yarnUsed: '', status: 'In Progress' });

  const handleAddProject = (e) => {
    e.preventDefault();
    if (!newProject.name) {
      alert("Project name is required."); // Replaced with Modal in next iteration
      return;
    }
    setProjects([...projects, { ...newProject, id: projects.length + 1 }]);
    setNewProject({ name: '', pattern: '', yarnUsed: '', status: 'In Progress' });
    setIsAddingProject(false);
  };

  return (
    <div className="p-4 sm:p-6 bg-gray-50 min-h-screen">
      <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center sm:text-left">My Projects</h2>

      <button
        onClick={() => setIsAddingProject(true)}
        className="flex items-center justify-center px-4 py-2 mb-6 bg-indigo-600 text-white rounded-lg shadow-md hover:bg-indigo-700 transition duration-150 ease-in-out w-full sm:w-auto"
      >
        <PlusCircleIcon className="mr-2" /> Add New Project
      </button>

      <Modal isOpen={isAddingProject} onClose={() => setIsAddingProject(false)} title="Add New Project">
        <form onSubmit={handleAddProject} className="space-y-4">
          <div>
            <label htmlFor="projectName" className="block text-sm font-medium text-gray-700">Project Name</label>
            <input
              type="text"
              id="projectName"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              value={newProject.name}
              onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="pattern" className="block text-sm font-medium text-gray-700">Pattern Used</label>
            <input
              type="text"
              id="pattern"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              value={newProject.pattern}
              onChange={(e) => setNewProject({ ...newProject, pattern: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="yarnUsed" className="block text-sm font-medium text-gray-700">Yarn Used (e.g., "Merino Worsted - Blue (2 skeins)")</label>
            <input
              type="text"
              id="yarnUsed"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              value={newProject.yarnUsed}
              onChange={(e) => setNewProject({ ...newProject, yarnUsed: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="status" className="block text-sm font-medium text-gray-700">Status</label>
            <select
              id="status"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              value={newProject.status}
              onChange={(e) => setNewProject({ ...newProject, status: e.target.value })}
            >
              <option value="In Progress">In Progress</option>
              <option value="Completed">Completed</option>
              <option value="Planned">Planned</option>
              <option value="On Hold">On Hold</option>
            </select>
          </div>
          <button
            type="submit"
            className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition duration-150 ease-in-out"
          >
            Add Project
          </button>
        </form>
      </Modal>

      {projects.length === 0 ? (
        <p className="text-gray-600 text-center py-8">No projects added yet! Click "Add New Project" to plan your next craft.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div key={project.id} className="bg-white rounded-xl shadow-md p-4 border border-gray-200">
              <h3 className="font-semibold text-lg text-gray-800 mb-1">{project.name}</h3>
              <p className="text-sm text-gray-600">Pattern: {project.pattern || 'N/A'}</p>
              <p className="text-sm text-gray-600">Yarn: {project.yarnUsed || 'N/A'}</p>
              <p className="text-sm text-gray-600">Status: <span className={`font-medium ${project.status === 'Completed' ? 'text-green-600' : 'text-orange-600'}`}>{project.status}</span></p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Main App Component
function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const { userId } = useContext(FirebaseContext); // Get userId from context

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomeFeed />;
      case 'stash':
        return <StashOrganizer />;
      case 'projects':
        return <ProjectOrganizer />;
      default:
        return <HomeFeed />;
    }
  };

  return (
    <div className="font-sans antialiased text-gray-900 bg-gray-100 min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm py-4 px-6 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center">
          {/* Using the provided logo image */}
          <img
            src="uploaded:ChatGPT Image Jun 6, 2025, 07_47_07 AM.jpg-731aba23-a5ba-40cf-9412-6fcde464dc82"
            alt="CraftGrab Logo"
            className="h-10 w-10 mr-3 rounded-full"
            onError={(e) => { e.target.onerror = null; e.target.src = `https://placehold.co/40x40/ffffff/000000?text=CG` }}
          />
          <h1 className="text-2xl font-bold text-indigo-700">CraftGrab</h1>
        </div>
        <div className="flex items-center text-sm text-gray-500">
          {userId && (
            <span className="mr-2 hidden md:block">User ID: <span className="font-mono">{userId}</span></span>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow">
        {renderPage()}
      </main>

      {/* Bottom Navigation for Mobile */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg sm:hidden z-20">
        <ul className="flex justify-around items-center h-16">
          <li>
            <button
              onClick={() => setCurrentPage('home')}
              className={`flex flex-col items-center text-sm px-2 py-1 rounded-md transition duration-150 ease-in-out ${currentPage === 'home' ? 'text-indigo-700 font-semibold' : 'text-gray-500 hover:text-indigo-700'}`}
            >
              <HomeIcon className="h-6 w-6 mb-1" />
              Home
            </button>
          </li>
          <li>
            <button
              onClick={() => setCurrentPage('stash')}
              className={`flex flex-col items-center text-sm px-2 py-1 rounded-md transition duration-150 ease-in-out ${currentPage === 'stash' ? 'text-indigo-700 font-semibold' : 'text-gray-500 hover:text-indigo-700'}`}
            >
              <BoxIcon className="h-6 w-6 mb-1" />
              Stash
            </button>
          </li>
          <li>
            <button
              onClick={() => setCurrentPage('projects')}
              className={`flex flex-col items-center text-sm px-2 py-1 rounded-md transition duration-150 ease-in-out ${currentPage === 'projects' ? 'text-indigo-700 font-semibold' : 'text-gray-500 hover:text-indigo-700'}`}
            >
              <FolderIcon className="h-6 w-6 mb-1" />
              Projects
            </button>
          </li>
        </ul>
      </nav>

      {/* Sidebar Navigation for Desktop */}
      <nav className="hidden sm:block fixed left-0 top-0 h-full w-60 bg-white shadow-lg pt-20 z-0">
        <ul className="flex flex-col p-4 space-y-2">
          <li>
            <button
              onClick={() => setCurrentPage('home')}
              className={`flex items-center text-base px-4 py-2 rounded-lg w-full text-left transition duration-150 ease-in-out ${currentPage === 'home' ? 'bg-indigo-100 text-indigo-700 font-semibold' : 'text-gray-600 hover:bg-gray-50 hover:text-indigo-700'}`}
            >
              <HomeIcon className="h-5 w-5 mr-3" />
              Home Feed
            </button>
          </li>
          <li>
            <button
              onClick={() => setCurrentPage('stash')}
              className={`flex items-center text-base px-4 py-2 rounded-lg w-full text-left transition duration-150 ease-in-out ${currentPage === 'stash' ? 'bg-indigo-100 text-indigo-700 font-semibold' : 'text-gray-600 hover:bg-gray-50 hover:text-indigo-700'}`}
            >
              <BoxIcon className="h-5 w-5 mr-3" />
              Stash Organizer
            </button>
          </li>
          <li>
            <button
              onClick={() => setCurrentPage('projects')}
              className={`flex items-center text-base px-4 py-2 rounded-lg w-full text-left transition duration-150 ease-in-out ${currentPage === 'projects' ? 'bg-indigo-100 text-indigo-700 font-semibold' : 'text-gray-600 hover:bg-gray-50 hover:text-indigo-700'}`}
            >
              <FolderIcon className="h-5 w-5 mr-3" />
              Project Organizer
            </button>
          </li>
        </ul>
      </nav>
      {/* Spacer for desktop sidebar */}
      <div className="hidden sm:block w-60 flex-shrink-0"></div>
    </div>
  );
}

// Wrap the App component with FirebaseProvider to make Firebase services available
export default function WrappedApp() {
  return (
    <FirebaseProvider>
      <App />
    </FirebaseProvider>
  );
}
