import { Routes, Route, NavLink } from 'react-router-dom';
import Upload from './pages/Upload/Upload';
import Companies from './pages/Companies/Companies';
import Analytics from './pages/Analytics/Analytics';
import Decisions from './pages/Decisions/Decisions';

function Navbar() {
    return (
        <nav className="navbar">
            <div className="navbar-content">
                <div className="navbar-brand">
                    <div className="navbar-logo">ING</div>
                    <span className="navbar-title">ESG Risk Assessment</span>
                </div>
                <div className="navbar-nav">
                    <NavLink
                        to="/"
                        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                        end
                    >
                        Upload
                    </NavLink>
                    <NavLink
                        to="/companies"
                        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                    >
                        Companies
                    </NavLink>
                    <NavLink
                        to="/analytics"
                        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                    >
                        Analytics
                    </NavLink>
                    <NavLink
                        to="/decisions"
                        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                    >
                        Decisions
                    </NavLink>
                </div>
            </div>
        </nav>
    );
}

function App() {
    return (
        <div className="app-container">
            <Navbar />
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<Upload />} />
                    <Route path="/companies" element={<Companies />} />
                    <Route path="/analytics" element={<Analytics />} />
                    <Route path="/decisions" element={<Decisions />} />
                </Routes>
            </main>
        </div>
    );
}

export default App;
