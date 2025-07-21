import '../styles/Profiles.css';

export default function Profiles({ profile }) {
  if (!profile) return <div className="no-profile">Select an area to view details.</div>;

  return (
    <div className="profile-card">
      <h2>{profile.areaName}</h2>
      <ul>
        {Object.entries(profile.indicators).map(([key, val]) => (
          <li key={key}>
            <strong>{key}:</strong> {val}
          </li>
        ))}
      </ul>
    </div>
  );
}
