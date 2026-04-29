import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import '../styles/Sidebar.css';

export default function Sidebar() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    // Force a full reload so no in-memory chat state leaks
    // between users after logout/login.
    navigate('/', { replace: true });
    window.location.reload();
  };

  return (
    <aside className="sidebar">
      {/* BFI brand mark */}
      <div className="sidebar-logo">
        <svg width="22" height="17" viewBox="149 28 22 18" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M164.637 32.512L159.655 29.2289C158.743 28.6271 157.531 29.2819 157.531 30.3704V36.6979C157.531 37.7687 158.708 38.4235 159.619 37.866L164.602 34.8218C165.46 34.2996 165.478 33.0607 164.637 32.5032V32.512Z" fill="#0E0E11"/>
          <path d="M151.628 34.3704C150.735 34.3704 150 35.0961 150 35.9988V42.7067C150 43.6005 150.726 44.335 151.628 44.335C154.381 44.335 156.611 42.105 156.611 39.3527C156.611 36.6005 154.381 34.3704 151.628 34.3704Z" fill="#0E0E11"/>
          <path d="M167.363 36.1581H167.354C165.898 36.1581 164.717 37.3388 164.717 38.7952V41.6979C164.717 43.1543 165.898 44.335 167.354 44.335H167.363C168.819 44.335 170 43.1543 170 41.6979V38.7952C170 37.3388 168.819 36.1581 167.363 36.1581Z" fill="#0E0E11"/>
        </svg>
      </div>

      {/* Icon-only nav */}
      <nav className="sidebar-nav">
        {/* My Sources — database/stacked-cylinders icon */}
        <NavLink
          to="/upload"
          className={({ isActive }) => `sidebar-nav-item${isActive ? ' active' : ''}`}
          title="My Sources"
        >
          <svg width="18" height="18" viewBox="52 2 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
            <path d="M53 10V14.375C53 14.375 53 17 59.9999 17C66.9998 17 66.9998 14.375 66.9998 14.375V10"/>
            <path d="M53 5.625L53.0002 10.0265C53.0002 10.0265 53.0001 12.5 60 12.5C66.9999 12.5 66.9999 10 66.9999 10V5.625"/>
            <path d="M60 3C67 3 66.9999 5.625 66.9999 5.625C66.9999 5.625 66.9999 8 60 8C53 8 53 5.625 53 5.625C53 5.625 53 3 60 3Z"/>
          </svg>
        </NavLink>

        {/* Queue — arrow + rounded-rect icon */}
        <NavLink
          to="/submissions"
          className={({ isActive }) => `sidebar-nav-item${isActive ? ' active' : ''}`}
          title="Queue"
        >
          <svg width="18" height="18" viewBox="26 163 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
            <path d="M28 167H42M42 167L39.6667 165M42 167L39.6667 169"/>
            <rect x="27.5" y="172.5" width="15" height="6" rx="1"/>
          </svg>
        </NavLink>

        {/* Edit — pencil icon */}
        <NavLink
          to="/settings"
          className={({ isActive }) => `sidebar-nav-item${isActive ? ' active' : ''}`}
          title="Settings"
        >
          <svg width="18" height="18" viewBox="77 56 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
            <path d="M85.7761 12.0557L83.3475 12.6628C82.7372 12.8154 82.1844 12.2626 82.3369 11.6523L82.9441 9.2236C82.9807 9.07707 83.0565 8.94326 83.1633 8.83646L88.5859 3.41389C89.3669 2.63284 90.6332 2.63284 91.4143 3.41389L91.5859 3.58546C92.3669 4.36651 92.3669 5.63284 91.5859 6.41388L86.1633 11.8365C86.0565 11.9433 85.9227 12.019 85.7761 12.0557Z"/>
            <path d="M92 12V15C92 16.1046 91.1046 17 90 17H80C78.8954 17 78 16.1046 78 15V5C78 3.89543 78.8954 3 80 3H83"/>
          </svg>
        </NavLink>
      </nav>

      {/* Avatar / logout at bottom */}
      <div className="sidebar-footer">
        <button className="sidebar-avatar-btn" onClick={handleLogout} title="Logout">
          <div className="sidebar-avatar-circle"></div>
        </button>
      </div>
    </aside>
  );
}
