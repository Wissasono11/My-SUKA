import type { SsoUser } from "@/lib/sso/session";

interface DashboardNavbarProps {
  user: SsoUser;
}

function getInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0))
    .join("")
    .toUpperCase() || "U";
}

export default function DashboardNavbar({ user }: DashboardNavbarProps) {
  const identityNumber = user.nim_nip?.trim() || user.id;

  return (
    <header className="dashboard-navbar">
      <div className="dashboard-navbar-inner">
        <a className="dashboard-brand" href="/dashboard" aria-label="My-SUKA Dashboard">
          <span className="dashboard-brand-mark" aria-hidden="true">M</span>
          <span>My-SUKA</span>
        </a>

        <div className="dashboard-account">
          <span className="dashboard-identity-number">{identityNumber}</span>
          <span className="dashboard-account-divider" aria-hidden="true" />

          <details className="profile-menu">
            <summary aria-label="Buka menu profil">
              {user.picture_url ? (
                // Google profile images are provided by the SSO identity provider.
                // eslint-disable-next-line @next/next/no-img-element
                <img className="profile-avatar" src={user.picture_url} alt="" referrerPolicy="no-referrer" />
              ) : (
                <span className="profile-avatar profile-avatar-fallback" aria-hidden="true">
                  {getInitials(user.name)}
                </span>
              )}
              <span className="profile-name">{user.name}</span>
              <span className="profile-chevron" aria-hidden="true">⌄</span>
            </summary>

            <div className="profile-dropdown">
              <div className="profile-dropdown-user">
                <strong>{user.name}</strong>
                <span>{user.email}</span>
              </div>
              <form method="post" action="/api/sso/logout">
                <button className="profile-logout" type="submit">
                  Logout
                </button>
              </form>
            </div>
          </details>
        </div>
      </div>
    </header>
  );
}
