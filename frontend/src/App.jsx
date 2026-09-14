import { useEffect, useMemo, useState } from 'react';
import {
  AcademicCapIcon, ArrowDownTrayIcon, ArrowLeftOnRectangleIcon, ArrowPathIcon,
  BellIcon, BookOpenIcon, ChartBarIcon, CheckCircleIcon, ChevronDownIcon,
  ChevronRightIcon, ClockIcon, Cog6ToothIcon, DocumentTextIcon,
  EyeIcon, FolderIcon, HomeIcon, LockClosedIcon, MagnifyingGlassIcon,
  MegaphoneIcon, MoonIcon, PencilSquareIcon, PlayCircleIcon, PlusIcon,
  QuestionMarkCircleIcon, ShieldCheckIcon, SunIcon, TrashIcon, UserCircleIcon,
  UsersIcon, VideoCameraIcon, XMarkIcon, Bars3Icon, ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import toast, { Toaster } from 'react-hot-toast';
import './index.css';

const API = 'https://qodekraft-learning-platform.onrender.com/api/v1';


const studentNav = [
  ['Dashboard', HomeIcon],
  ['My Learning', BookOpenIcon],
  ['Recorded Classes', VideoCameraIcon],
  ['Assignments', DocumentTextIcon],
  ['Quizzes', QuestionMarkCircleIcon],
  ['My Progress', ChartBarIcon],
  ['Certificates', ShieldCheckIcon],
];

const adminNav = [
  ['Dashboard', HomeIcon],
  ['Students', UsersIcon],
  ['Approval Requests', ShieldCheckIcon],
  ['Domains', AcademicCapIcon],
  ['Recordings', VideoCameraIcon],
  ['Assignments', DocumentTextIcon],
  ['Quizzes', QuestionMarkCircleIcon],
  ['Projects', FolderIcon],
  ['Announcements', MegaphoneIcon],
  ['Reports', ChartBarIcon],
  ['Platform Settings', Cog6ToothIcon],
  ['Manage Admins', UsersIcon],
];

async function downloadProtectedFile(path, filename) {
  const token = localStorage.getItem('qk_access_token');
  const response = await fetch(`${API}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error('Unable to download file');
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename || 'submission-file';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

async function request(path, options = {}, retry = true) {
  const token = localStorage.getItem('qk_access_token');

  const headers = new Headers(options.headers || {});

  if (
    !(options.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response;

  try {
    response = await fetch(`${API}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(
      'Cannot reach QODEKRAFT backend. Please try again.'
    );
  }

  if (
    response.status === 401 &&
    retry &&
    localStorage.getItem('qk_refresh_token')
  ) {
    try {
      const r = await fetch(`${API}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: localStorage.getItem('qk_refresh_token'),
        }),
      });

      if (r.ok) {
        const data = await r.json();

        localStorage.setItem(
          'qk_access_token',
          data.access_token
        );

        return request(path, options, false);
      }
    } catch {
      // Continue to logout below.
    }

    clearSession();
  }

  const text = await response.text();

  let data;

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = {
      detail: text,
    };
  }

  if (!response.ok) {
    // FastAPI validation errors may contain arrays/objects. Convert them
    // to a readable string before putting them into Error.message.
    const rawDetail = data?.detail;
    let message = data?.message;

    if (typeof rawDetail === 'string' && rawDetail.trim()) {
      message = rawDetail;
    } else if (Array.isArray(rawDetail)) {
      message = rawDetail
        .map((item) => {
          if (typeof item === 'string') return item;
          const location = Array.isArray(item?.loc)
            ? item.loc.filter(Boolean).join(' → ')
            : '';
          const msg = item?.msg || item?.message;
          return msg
            ? `${location ? `${location}: ` : ''}${msg}`
            : JSON.stringify(item);
        })
        .join('\n');
    } else if (rawDetail && typeof rawDetail === 'object') {
      message = rawDetail.message || rawDetail.msg || JSON.stringify(rawDetail);
    }

    if (!message) {
      message = `Request failed (${response.status})`;
    }

    throw new Error(message);
  }

  return data;
}

function clearSession() {
  [
    'qk_access_token',
    'qk_refresh_token',
    'qk_user',
  ].forEach((key) => {
    localStorage.removeItem(key);
  });
}

function saveSession(data) {
  localStorage.setItem(
    'qk_access_token',
    data.access_token
  );

  localStorage.setItem(
    'qk_refresh_token',
    data.refresh_token
  );

  localStorage.setItem(
    'qk_user',
    JSON.stringify(data)
  );
}

function userSession() {
  try {
    return JSON.parse(
      localStorage.getItem('qk_user') || 'null'
    );
  } catch {
    return null;
  }
}

function dateText(value) {
  if (!value) return '—';

  const d = new Date(value);

  if (Number.isNaN(d.getTime())) {
    return String(value);
  }

  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function money(value) {
  return value == null ? '—' : String(value);
}

function errorToast(error) {
  // FastAPI/Pydantic validation errors can arrive as an array of objects.
  // Never let JavaScript coerce those objects into the unhelpful
  // "[object Object]" message.
  const detail = error?.response?.data?.detail ?? error?.detail;
  let message = error?.message;

  if (Array.isArray(detail)) {
    message = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        const location = Array.isArray(item?.loc)
          ? item.loc.filter(Boolean).join(' → ')
          : '';
        return item?.msg
          ? `${location ? `${location}: ` : ''}${item.msg}`
          : JSON.stringify(item);
      })
      .join('\n');
  } else if (detail && typeof detail === 'object') {
    message = detail.msg || detail.message || JSON.stringify(detail);
  } else if (typeof detail === 'string' && detail.trim()) {
    message = detail;
  }

  toast.error(message || 'Something went wrong');
}

function Logo({ compact = false }) {
  return (
    <div className={`logo ${compact ? 'compact' : ''}`}>
      <img
        src="/qodekraft-logo.png"
        alt="QODEKRAFT"
        className="brand-logo"
      />
    </div>
  );
}

function Badge({ children, tone = 'blue' }) {
  return (
    <span className={`badge ${tone}`}>
      {children}
    </span>
  );
}

function EmptyState({
  icon: Icon = FolderIcon,
  title = 'No data yet',
  text = 'Nothing has been added to this workspace yet.',
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon />
      </div>

      <h3>{title}</h3>

      <p>{text}</p>
    </div>
  );
}

function Loading() {
  return (
    <div className="loading">
      <span />
      Loading…
    </div>
  );
}

function PageTitle({
  eyebrow,
  title,
  subtitle,
  action,
}) {
  return (
    <div className="page-title">
      <div>
        <div className="eyebrow">
          {eyebrow}
        </div>

        <h1>{title}</h1>

        {subtitle && (
          <p>{subtitle}</p>
        )}
      </div>

      {action}
    </div>
  );
}

function Stat({
  icon: Icon,
  label,
  value = 0,
  tone = 'blue',
}) {
  return (
    <div className="stat">
      <div className={`stat-icon ${tone}`}>
        <Icon />
      </div>

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function Button({
  children,
  variant = 'primary',
  icon: Icon,
  ...props
}) {
  return (
    <button
      className={`btn ${variant}`}
      {...props}
    >
      {Icon && <Icon />}
      {children}
    </button>
  );
}

function Field({
  label,
  children,
  hint,
}) {
  return (
    <label className="field">
      <span>{label}</span>

      {children}

      {hint && (
        <small>{hint}</small>
      )}
    </label>
  );
}

/* =========================================================
   AUTHENTICATION
   ========================================================= */

function AuthScreen({ onAuthenticated }) {
  const getInitialMode = () => {
    const hash = window.location.hash.toLowerCase();

    if (
      hash === '#/signup' ||
      hash === '#/register'
    ) {
      return 'signup';
    }

    return 'login';
  };

  const [mode, setMode] = useState(
    getInitialMode
  );

  const [role, setRole] = useState('student');

  const [show, setShow] = useState(false);

  const [busy, setBusy] = useState(false);

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    confirm_password: '',
    qualification: '',
    preferred_domain: '',
    role: 'student',
  });

  const set = (key, value) => {
    setForm((previous) => ({
      ...previous,
      [key]: value,
    }));
  };

  const openLogin = () => {
    setMode('login');
    window.location.hash = '#/login';
  };

  const openSignup = () => {
    if (role !== 'student') {
      toast.error(
        'Administrator accounts cannot be created here.'
      );
      return;
    }

    setMode('signup');
    window.location.hash = '#/signup';
  };

  useEffect(() => {
    const handleHashChange = () => {
      const hash =
        window.location.hash.toLowerCase();

      if (
        hash === '#/signup' ||
        hash === '#/register'
      ) {
        setRole('student');
        setMode('signup');
      } else if (hash === '#/login' || !hash) {
        setMode('login');
      }
    };

    window.addEventListener(
      'hashchange',
      handleHashChange
    );

    return () => {
      window.removeEventListener(
        'hashchange',
        handleHashChange
      );
    };
  }, []);

  const submit = async (event) => {
    event.preventDefault();

    if (busy) return;

    setBusy(true);

    try {
      if (mode === 'signup') {
        if (role !== 'student') {
          throw new Error(
            'Only student accounts can be registered.'
          );
        }

        if (form.password.length < 8) {
          throw new Error(
            'Password must be at least 8 characters long.'
          );
        }

        if (
          form.password !==
          form.confirm_password
        ) {
          throw new Error(
            'Passwords do not match.'
          );
        }

        const data = await request(
          '/auth/signup',
          {
            method: 'POST',
            body: JSON.stringify({
              full_name: form.full_name.trim(),
              email: form.email.trim().toLowerCase(),
              phone: form.phone.trim() || null,
              password: form.password,
              confirm_password:
                form.confirm_password,
              qualification:
                form.qualification.trim() || null,
              preferred_domain:
                form.preferred_domain.trim() || null,
              role: 'student',
            }),
          }
        );

        toast.success(
          data.message ||
          'Registration submitted. Wait for admin approval and domain assignment before logging in.'
        );

        setForm((previous) => ({
          ...previous,
          password: '',
          confirm_password: '',
        }));

        setMode('login');
        window.location.hash = '#/login';

        return;
      }

      const data = await request(
        '/auth/login',
        {
          method: 'POST',
          body: JSON.stringify({
            email: form.email.trim().toLowerCase(),
            password: form.password,
          }),
        },
        false
      );

      if (data.role !== role) {
        throw new Error(
          `This account is registered as ${data.role}. Select the correct login type.`
        );
      }

      /*
       * Students must be approved by an administrator.
       * Admin accounts can login normally.
       */
      if (
        data.role === 'student' &&
        data.status !== 'approved'
      ) {
        clearSession();

        onAuthenticated({
          pending: true,
          status: data.status,
          message: statusMessage(data.status),
        });

        return;
      }

      saveSession(data);

      onAuthenticated(data);
    } catch (error) {
      errorToast(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-brand-panel">
        <Logo />

        <div className="auth-copy">
          <span>
            LEARN · BUILD · GROW
          </span>

          <h1>
            Build skills that move your career
            forward.
          </h1>

          <p>
            QODEKRAFT is a private learning
            workspace for structured courses,
            practical projects, quizzes,
            recordings and hands-on learning
            practice.
          </p>

          <div className="auth-pills">
            <b>✓ Domain-based learning</b>
            <b>✓ Protected recordings</b>
            <b>✓ Progress tracking</b>
          </div>
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-card">
          <Logo compact />

          <h2>
            {mode === 'login'
              ? 'Welcome back'
              : 'Create your student account'}
          </h2>

          <p className="muted">
            {mode === 'login'
              ? 'Sign in to access your QODEKRAFT workspace.'
              : 'Create your student account. Your account will wait for administrator approval before you can access the learning dashboard.'}
          </p>

          <div className="role-tabs">
            <button
              type="button"
              className={
                role === 'student'
                  ? 'active'
                  : ''
              }
              onClick={() => {
                setRole('student');

                if (mode === 'signup') {
                  window.location.hash =
                    '#/signup';
                }
              }}
            >
              Student
            </button>

            <button
              type="button"
              className={
                role === 'admin'
                  ? 'active'
                  : ''
              }
              onClick={() => {
                setRole('admin');
                setMode('login');
                window.location.hash =
                  '#/login';
              }}
            >
              Admin
            </button>
          </div>

          <form
            onSubmit={submit}
            className="auth-form"
          >
            {mode === 'signup' && (
              <>
                <Field label="Full name *">
                  <input
                    value={form.full_name}
                    onChange={(e) =>
                      set(
                        'full_name',
                        e.target.value
                      )
                    }
                    placeholder="Your full name"
                    required
                  />
                </Field>

                <Field label="Phone">
                  <input
                    value={form.phone}
                    onChange={(e) =>
                      set(
                        'phone',
                        e.target.value
                      )
                    }
                    placeholder="Optional phone number"
                  />
                </Field>

                <Field label="Qualification">
                  <input
                    value={form.qualification}
                    onChange={(e) =>
                      set(
                        'qualification',
                        e.target.value
                      )
                    }
                    placeholder="B.Tech, B.Sc, MCA…"
                  />
                </Field>

                <Field label="Preferred domain">
                  <input
                    value={form.preferred_domain}
                    onChange={(e) =>
                      set(
                        'preferred_domain',
                        e.target.value
                      )
                    }
                    placeholder="AI, Data Science, Python…"
                  />
                </Field>
              </>
            )}

            <Field label="Email address *">
              <input
                type="email"
                value={form.email}
                onChange={(e) =>
                  set(
                    'email',
                    e.target.value
                  )
                }
                placeholder="you@example.com"
                required
              />
            </Field>

            <Field label="Password *">
              <div className="password">
                <input
                  type={
                    show
                      ? 'text'
                      : 'password'
                  }
                  value={form.password}
                  onChange={(e) =>
                    set(
                      'password',
                      e.target.value
                    )
                  }
                  placeholder="Enter your password"
                  required
                  minLength={8}
                />

                <button
                  type="button"
                  onClick={() =>
                    setShow(!show)
                  }
                >
                  {show ? 'Hide' : 'Show'}
                </button>
              </div>
            </Field>

            {mode === 'signup' && (
              <Field label="Confirm password *">
                <input
                  type="password"
                  value={form.confirm_password}
                  onChange={(e) =>
                    set(
                      'confirm_password',
                      e.target.value
                    )
                  }
                  placeholder="Repeat your password"
                  required
                />
              </Field>
            )}

            <Button
              type="submit"
              disabled={busy}
              className="full"
            >
              {busy
                ? 'Please wait…'
                : mode === 'signup'
                  ? 'Create Student Account'
                  : `Sign in as ${
                      role === 'admin'
                        ? 'Admin'
                        : 'Student'
                    }`}
            </Button>
          </form>

          {role === 'student' && (
            <div className="auth-switch">
              {mode === 'login' ? (
                <>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={openSignup}
                  >
                    Create account
                  </button>
                </>
              ) : (
                <>
                  Already registered?{' '}
                  <button
                    type="button"
                    onClick={openLogin}
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>
          )}

          {role === 'admin' && (
            <div className="auth-note">
              <LockClosedIcon />

              Administrator accounts are
              login-only. New admin accounts
              cannot be created from this page.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function statusMessage(status) {
  return {
    pending:
      'Your account is waiting for administrator approval.',
    rejected:
      'Your registration was rejected. Contact the administrator.',
    blocked:
      'Your account is blocked. Contact the administrator.',
    suspended:
      'Your account is suspended. Contact the administrator.',
  }[status] ||
    'Account access is currently unavailable.';
}

function PendingScreen({
  info,
  onBack,
}) {
  return (
    <div className="status-screen">
      <Logo />

      <div className="status-card">
        <div className="status-icon">
          <ClockIcon />
        </div>

        <h1>
          Account access is not active
        </h1>

        <p>{info.message}</p>

        <Badge
          tone={
            info.status === 'pending'
              ? 'amber'
              : 'red'
          }
        >
          {info.status}
        </Badge>

        <Button
          variant="outline"
          icon={ArrowLeftOnRectangleIcon}
          onClick={onBack}
        >
          Back to login
        </Button>
      </div>
    </div>
  );
}

function InstallQodekraft() {
  const [deferred, setDeferred] = useState(null);
  const [installed, setInstalled] = useState(false);
  useEffect(() => {
    const onBefore = (e) => { e.preventDefault(); setDeferred(e); };
    const onInstalled = () => { setInstalled(true); setDeferred(null); };
    window.addEventListener("beforeinstallprompt", onBefore);
    window.addEventListener("appinstalled", onInstalled);
    if (window.matchMedia && (window.matchMedia("(display-mode: standalone)").matches || window.matchMedia("(display-mode: fullscreen)").matches || window.matchMedia("(display-mode: minimal-ui)").matches)) setInstalled(true);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBefore);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);
  if (installed) return null;
  const install = async () => {
    if (deferred) { deferred.prompt(); try { await deferred.userChoice; } catch {} setDeferred(null); }
    else toast.info("Open Chrome or Edge menu and choose Install QODEKRAFT. The app must be served from localhost or HTTPS.");
  };
  return <button className="install-btn" onClick={install} title="Install QODEKRAFT"><ArrowDownTrayIcon/><span>Install QODEKRAFT</span></button>;
}

/* =========================================================
   APP
   ========================================================= */

function App() {
  const [session, setSession] =
    useState(userSession());

  const [statusInfo, setStatusInfo] =
    useState(null);

  const [page, setPage] =
    useState('Dashboard');

  const [dark, setDark] =
    useState(
      () =>
        localStorage.getItem(
          'qk_theme'
        ) === 'dark'
    );

  const [mobile, setMobile] =
    useState(false);

  const [profileOpen, setProfileOpen] =
    useState(false);

  const role =
    session?.role || 'student';

  const nav =
    role === 'admin'
      ? adminNav
      : studentNav;

  useEffect(() => {
    document.documentElement.classList.toggle(
      'dark',
      dark
    );

    localStorage.setItem(
      'qk_theme',
      dark ? 'dark' : 'light'
    );
  }, [dark]);

  if (statusInfo) {
    return (
      <PendingScreen
        info={statusInfo}
        onBack={() =>
          setStatusInfo(null)
        }
      />
    );
  }

  if (!session) {
    return (
      <>
        <Toaster position="top-right" />

        <AuthScreen
          onAuthenticated={(data) =>
            data.pending
              ? setStatusInfo(data)
              : setSession(data)
          }
        />
      </>
    );
  }

  const logout = () => {
    clearSession();
    setSession(null);
    setPage('Dashboard');
  };

  const go = (nextPage) => {
    setPage(nextPage);
    setMobile(false);
    setProfileOpen(false);
  };

  return (
    <div className="app">
      <Toaster position="top-right" />

      <aside
        className={`sidebar ${
          mobile ? 'open' : ''
        }`}
      >
        <div className="side-head">
          <Logo />

          <button
            className="mobile-close"
            onClick={() =>
              setMobile(false)
            }
          >
            <XMarkIcon />
          </button>
        </div>

        <div className="side-label">
          {role === 'admin'
            ? 'ADMIN PANEL'
            : 'LEARNING SPACE'}
        </div>

        <nav>
          {nav.map(
            ([name, Icon]) => (
              <button
                key={name}
                className={
                  page === name
                    ? 'active'
                    : ''
                }
                onClick={() =>
                  go(name)
                }
              >
                <Icon />
                <span>{name}</span>
              </button>
            )
          )}
        </nav>

        {role === 'student' && (
          <>
            <div className="side-label">
              EXPLORE
            </div>

            <nav>
              <button
                className={
                  page === 'Domains'
                    ? 'active'
                    : ''
                }
                onClick={() =>
                  go('Domains')
                }
              >
                <AcademicCapIcon />
                <span>Domains</span>
              </button>

              <button
                className={
                  page === 'Projects'
                    ? 'active'
                    : ''
                }
                onClick={() =>
                  go('Projects')
                }
              >
                <FolderIcon />
                <span>Projects</span>
              </button>

              <button
                className={
                  page === 'Announcements'
                    ? 'active'
                    : ''
                }
                onClick={() =>
                  go('Announcements')
                }
              >
                <MegaphoneIcon />
                <span>Announcements</span>
              </button>
            </nav>
          </>
        )}

        <div className="side-spacer" />

        <div className="quote">
          “Practice
          <br />
          Build
          <br />
          Grow”
          <small>
            — QODEKRAFT
          </small>
        </div>

        <button
          className="logout"
          onClick={logout}
        >
          <ArrowLeftOnRectangleIcon />
          Logout
        </button>
      </aside>

      <main className="main">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() =>
              setMobile(true)
            }
          >
            <Bars3Icon />
          </button>

          <div className="global-search">
            <MagnifyingGlassIcon />

            <input
              placeholder={
                role === 'admin'
                  ? 'Search students, domains, content…'
                  : 'Search your learning…'
              }
            />
            <InstallQodekraft />
          </div>

          <div className="top-right">
            <button
              className="icon-btn"
              title="Notifications"
            >
              <BellIcon />
            </button>

            <button
              className="icon-btn"
              title="Theme"
              onClick={() =>
                setDark(!dark)
              }
            >
              {dark ? (
                <SunIcon />
              ) : (
                <MoonIcon />
              )}
            </button>

            <button
              className="user-btn"
              onClick={() =>
                setProfileOpen(
                  !profileOpen
                )
              }
            >
              <div className="avatar">
                {role === 'admin'
                  ? 'A'
                  : (
                      session.full_name ||
                      'S'
                    )
                      .slice(0, 1)
                      .toUpperCase()}
              </div>

              <span>
                {session.full_name ||
                  (role === 'admin'
                    ? 'Admin'
                    : 'Student')}

                <small>
                  {role === 'admin'
                    ? 'Administrator'
                    : 'Learner'}
                </small>
              </span>

              <ChevronDownIcon />
            </button>
          </div>

          {profileOpen && (
            <div className="user-menu">
              <button
                onClick={() =>
                  go('Profile')
                }
              >
                <UserCircleIcon />
                Profile
              </button>

              {role === 'admin' && (
                <button
                  onClick={() =>
                    go(
                      'Platform Settings'
                    )
                  }
                >
                  <Cog6ToothIcon />
                  Platform settings
                </button>
              )}

              <button
                className="danger"
                onClick={logout}
              >
                <ArrowLeftOnRectangleIcon />
                Logout
              </button>
            </div>
          )}
        </header>

        <div className="content">
          {role === 'admin' ? (
            <AdminPage
              page={page}
              go={go}
            />
          ) : (
            <StudentPage
              page={page}
              go={go}
              session={session}
            />
          )}
        </div>
      </main>
    </div>
  );
}

/* =========================================================
   STUDENT
   ========================================================= */

function StudentPage({
  page,
  go,
  session,
}) {
  if (page === 'Dashboard') {
    return <StudentDashboard go={go} />;
  }

  if (
    page === 'My Learning' ||
    page === 'Domains'
  ) {
    return <StudentDomains go={go} />;
  }

  if (page === 'Recorded Classes') {
    return <StudentRecordings />;
  }

  if (page === 'Assignments') {
    return <StudentAssignments />;
  }

  if (page === 'Quizzes') {
    return <StudentQuizzes />;
  }


  if (page === 'My Progress') {
    return <StudentProgress />;
  }

  if (page === 'Projects') {
    return <StudentProjects />;
  }

  if (page === 'Announcements') {
    return <StudentAnnouncements />;
  }

  if (page === 'Certificates') {
    return (
      <EmptyState
        icon={ShieldCheckIcon}
        title="No certificates yet"
        text="Certificates will appear here when your completed learning requirements qualify."
      />
    );
  }

  if (page === 'Profile') {
    return <Profile session={session} />;
  }

  return <EmptyState />;
}

function useDomains() {
  const [domains, setDomains] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  useEffect(() => {
    let alive = true;

    request('/student/domains')
      .then((data) => {
        if (alive) {
          setDomains(data);
        }
      })
      .catch(() => {
        if (alive) {
          setDomains([]);
        }
      })
      .finally(() => {
        if (alive) {
          setLoading(false);
        }
      });

    return () => {
      alive = false;
    };
  }, []);

  return {
    domains,
    loading,
  };
}

function DomainPicker({
  domains,
  value,
  onChange,
}) {
  return (
    <select
      value={value || ''}
      onChange={(e) =>
        onChange(
          Number(e.target.value)
        )
      }
      disabled={!domains.length}
    >
      <option value="">
        {domains.length
          ? 'Select assigned domain'
          : 'No assigned domains'}
      </option>

      {domains.map((domain) => (
        <option
          key={domain.id}
          value={domain.id}
        >
          {domain.name}
        </option>
      ))}
    </select>
  );
}

function StudentDashboard({ go }) {
  const [data, setData] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  useEffect(() => {
    request('/student/dashboard')
      .then(setData)
      .catch(errorToast)
      .finally(() =>
        setLoading(false)
      );
  }, []);

  if (loading) {
    return <Loading />;
  }

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / STUDENT"
        title={`Welcome${
          data?.student_name
            ? `, ${data.student_name}`
            : ''
        }`}
        subtitle="Your assigned learning workspace, progress and upcoming work."
      />

      <section className="stats-grid">
        <Stat
          icon={AcademicCapIcon}
          label="Assigned domains"
          value={
            data?.domains_count ?? 0
          }
        />

        <Stat
          icon={BellIcon}
          label="Unread notifications"
          value={
            data?.unread_notifications ??
            0
          }
          tone="amber"
        />

        <Stat
          icon={VideoCameraIcon}
          label="Continue watching"
          value={
            data?.continue_watching
              ?.length ?? 0
          }
          tone="violet"
        />

        <Stat
          icon={DocumentTextIcon}
          label="Pending assignments"
          value={
            data?.pending_assignments
              ?.length ?? 0
          }
          tone="green"
        />
      </section>

      <div className="two-col">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>
                Continue learning
              </h2>

              <p>
                Resume classes you have
                already started.
              </p>
            </div>

            <Button
              variant="ghost"
              onClick={() =>
                go('Recorded Classes')
              }
            >
              View classes
              <ChevronRightIcon />
            </Button>
          </div>

          {data?.continue_watching
            ?.length ? (
            data.continue_watching.map(
              (item) => (
                <div
                  className="list-row"
                  key={item.recording_id}
                >
                  <div className="row-icon">
                    <PlayCircleIcon />
                  </div>

                  <div className="row-main">
                    <strong>
                      {item.title}
                    </strong>

                    <Progress
                      value={
                        item.percentage
                      }
                    />

                    <small>
                      {Math.round(
                        item.percentage
                      )}
                      % watched
                    </small>
                  </div>
                </div>
              )
            )
          ) : (
            <EmptyState
              icon={PlayCircleIcon}
              title="Nothing to resume"
              text="Your started recordings will appear here."
            />
          )}
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>
                Upcoming work
              </h2>

              <p>
                Assignments that still
                need your attention.
              </p>
            </div>
          </div>

          {data?.pending_assignments
            ?.length ? (
            data.pending_assignments.map(
              (item) => (
                <div
                  className="simple-row"
                  key={item.id}
                >
                  <DocumentTextIcon />

                  <div>
                    <strong>
                      {item.title}
                    </strong>

                    <small>
                      Due{' '}
                      {dateText(
                        item.due_date
                      )}
                    </small>
                  </div>
                </div>
              )
            )
          ) : (
            <EmptyState
              icon={CheckCircleIcon}
              title="No pending assignments"
              text="You are all caught up."
            />
          )}
        </section>
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>
              Latest announcements
            </h2>

            <p>
              Important updates for your
              learning workspace.
            </p>
          </div>

          <Button
            variant="ghost"
            onClick={() =>
              go('Announcements')
            }
          >
            View all
            <ChevronRightIcon />
          </Button>
        </div>

        {data?.announcements?.length ? (
          <div className="announcement-list">
            {data.announcements.map(
              (announcement) => (
                <div
                  className="announcement-row"
                  key={announcement.id}
                >
                  <MegaphoneIcon />

                  <div>
                    <strong>
                      {announcement.title}
                    </strong>

                    <small>
                      {dateText(
                        announcement.created_at
                      )}
                    </small>
                  </div>
                </div>
              )
            )}
          </div>
        ) : (
          <EmptyState
            icon={MegaphoneIcon}
            title="No announcements"
            text="Published announcements will appear here."
          />
        )}
      </section>
    </>
  );
}

function StudentDomains({ go }) {
  const {
    domains,
    loading,
  } = useDomains();

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / MY LEARNING"
        title="My Learning"
        subtitle="Only domains assigned to your account are shown."
      />

      <section className="domain-grid">
        {loading ? (
          <Loading />
        ) : domains.length ? (
          domains.map((domain) => (
            <article
              className="domain-card"
              key={domain.id}
            >
              <div className="domain-icon">
                <AcademicCapIcon />
              </div>

              <div>
                <h3>
                  {domain.name}
                </h3>

                <p>
                  {domain.description ||
                    'Learning content assigned by your administrator.'}
                </p>

                <div className="domain-meta">
                  <Badge tone="green">
                    Active access
                  </Badge>

                  {domain.access_expires_at && (
                    <span>
                      Access until{' '}
                      {dateText(
                        domain.access_expires_at
                      )}
                    </span>
                  )}
                </div>
              </div>

              <Button
                variant="outline"
                onClick={() =>
                  go('Recorded Classes')
                }
              >
                Open learning
                <ChevronRightIcon />
              </Button>
            </article>
          ))
        ) : (
          <EmptyState
            icon={AcademicCapIcon}
            title="No domains assigned"
            text="Your administrator has not assigned a learning domain to your account yet."
          />
        )}
      </section>
    </>
  );
}

function StudentRecordings() {
  const {
    domains,
    loading: domainsLoading,
  } = useDomains();

  const [domainId, setDomainId] =
    useState('');

  const [items, setItems] =
    useState([]);

  const [loading, setLoading] =
    useState(false);

  const [playing, setPlaying] =
    useState(null);

  useEffect(() => {
    if (
      !domainId &&
      domains.length
    ) {
      setDomainId(
        String(domains[0].id)
      );
    }
  }, [domains, domainId]);

  useEffect(() => {
    if (!domainId) {
      setItems([]);
      return;
    }

    setLoading(true);

    request(
      `/student/recordings?domain_id=${domainId}`
    )
      .then(setItems)
      .catch(errorToast)
      .finally(() =>
        setLoading(false)
      );
  }, [domainId]);

  const openVideo = async (item) => {
    try {
      const token =
        localStorage.getItem(
          'qk_access_token'
        );

      const response = await fetch(
        `${API}/student/recordings/${item.id}/stream`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const text =
          await response.text();

        throw new Error(
          text ||
          `Video unavailable (${response.status})`
        );
      }

      const blob =
        await response.blob();

      setPlaying({
        ...item,
        url: URL.createObjectURL(
          blob
        ),
      });
    } catch (error) {
      errorToast(error);
    }
  };

  if (domainsLoading) {
    return <Loading />;
  }

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / LEARNING"
        title="Recorded Classes"
        subtitle="Protected recordings are available only for your assigned domains."
        action={
          <DomainPicker
            domains={domains}
            value={domainId}
            onChange={(id) =>
              setDomainId(
                String(id)
              )
            }
          />
        }
      />

      {loading ? (
        <Loading />
      ) : items.length ? (
        <div className="recording-grid">
          {items.map((recording) => (
            <article
              className="recording-card"
              key={recording.id}
            >
              <div className="recording-cover">
                <VideoCameraIcon />

                <button
                  onClick={() =>
                    openVideo(recording)
                  }
                >
                  <PlayCircleIcon />
                </button>
              </div>

              <div className="recording-body">
                <div className="recording-top">
                  <Badge>
                    {recording.class_number
                      ? `Class ${recording.class_number}`
                      : 'Recording'}
                  </Badge>

                  {recording.progress
                    ?.is_completed && (
                    <Badge tone="green">
                      Completed
                    </Badge>
                  )}
                </div>

                <h3>
                  {recording.title}
                </h3>

                <p>
                  {recording.description ||
                    recording.topic ||
                    'Recorded learning session'}
                </p>

                <Progress
                  value={
                    recording.progress
                      ?.percentage || 0
                  }
                />

                <small>
                  {Math.round(
                    recording.progress
                      ?.percentage || 0
                  )}
                  % watched
                </small>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={VideoCameraIcon}
          title="No recordings available"
          text={
            domainId
              ? 'Your administrator has not published recordings for this domain yet.'
              : 'Select an assigned domain to view recordings.'
          }
        />
      )}

      {playing && (
        <VideoModal
          item={playing}
          onClose={() => {
            URL.revokeObjectURL(
              playing.url
            );

            setPlaying(null);
          }}
        />
      )}
    </>
  );
}

function VideoModal({
  item,
  onClose,
}) {
  const [seconds, setSeconds] =
    useState(
      item.progress
        ?.watched_seconds || 0
    );

  const complete = async () => {
    try {
      await request(
        `/student/recordings/${item.id}/complete`,
        {
          method: 'POST',
        }
      );

      toast.success(
        'Class marked complete'
      );
    } catch (error) {
      errorToast(error);
    }
  };

  const update = async (event) => {
    const time = Math.floor(
      event.currentTarget
        .currentTime || 0
    );

    setSeconds(time);

    if (time % 10 === 0) {
      request(
        `/student/recordings/${item.id}/progress?watched_seconds=${time}&duration_seconds=${Math.floor(
          event.currentTarget.duration ||
            item.duration_seconds ||
            1
        )}`,
        {
          method: 'POST',
        }
      ).catch(() => {});
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="video-modal">
        <div className="modal-head">
          <div>
            <h2>
              {item.title}
            </h2>

            <p>
              {seconds}s watched
            </p>
          </div>

          <button onClick={onClose}>
            <XMarkIcon />
          </button>
        </div>

        <video
          src={item.url}
          controls
          autoPlay
          onTimeUpdate={update}
        />

        <div className="modal-actions">
          <Button
            onClick={complete}
            icon={CheckCircleIcon}
          >
            Mark completed
          </Button>

          <Button
            variant="outline"
            onClick={onClose}
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

function StudentAssignments() {
  const {
    domains,
    loading: domainLoading,
  } = useDomains();

  const [domainId, setDomainId] =
    useState('');

  const [items, setItems] =
    useState([]);

  const [loading, setLoading] =
    useState(false);

  const [selected, setSelected] =
    useState(null);

  useEffect(() => {
    if (
      !domainId &&
      domains.length
    ) {
      setDomainId(
        String(domains[0].id)
      );
    }
  }, [domains, domainId]);

  useEffect(() => {
    if (!domainId) {
      setItems([]);
      return;
    }

    setLoading(true);

    request(
      `/student/assignments?domain_id=${domainId}`
    )
      .then(setItems)
      .catch(errorToast)
      .finally(() =>
        setLoading(false)
      );
  }, [domainId]);

  if (domainLoading) {
    return <Loading />;
  }

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / WORK"
        title="Assignments"
        subtitle="Submit work only to assignments published for your assigned domain."
        action={
          <DomainPicker
            domains={domains}
            value={domainId}
            onChange={(id) =>
              setDomainId(
                String(id)
              )
            }
          />
        }
      />

      {loading ? (
        <Loading />
      ) : items.length ? (
        <div className="cards-list">
          {items.map((assignment) => (
            <article
              className="content-card"
              key={assignment.id}
            >
              <div className="card-icon">
                <DocumentTextIcon />
              </div>

              <div className="card-main">
                <div className="card-line">
                  <h3>
                    {assignment.title}
                  </h3>

                  <Badge
                    tone={
                      assignment.submission
                        ? 'green'
                        : 'amber'
                    }
                  >
                    {assignment.submission
                      ?.status ||
                      'Not submitted'}
                  </Badge>
                </div>

                <p>
                  {assignment.description ||
                    assignment.topic ||
                    'Assignment details will be shown here.'}
                </p>

                <div className="meta-line">
                  <span>
                    Due{' '}
                    {dateText(
                      assignment.due_date
                    )}
                  </span>

                  <span>
                    {money(
                      assignment.max_marks
                    )}{' '}
                    marks
                  </span>
                </div>
              </div>

              <Button
                variant="outline"
                onClick={() =>
                  setSelected(
                    assignment
                  )
                }
              >
                Open
              </Button>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={DocumentTextIcon}
          title="No assignments yet"
          text="Published assignments for your assigned domain will appear here."
        />
      )}

      {selected && (
        <AssignmentModal
          assignment={selected}
          onClose={() =>
            setSelected(null)
          }
          onDone={() => {
            setSelected(null);

            if (domainId) {
              request(
                `/student/assignments?domain_id=${domainId}`
              )
                .then(setItems)
                .catch(() => {});
            }
          }}
        />
      )}
    </>
  );
}

function AssignmentModal({
  assignment,
  onClose,
  onDone,
}) {
  const [files, setFiles] =
    useState([]);

  const [busy, setBusy] =
    useState(false);

  const submit = async () => {
    if (!files.length) {
      toast.error(
        'Select at least one file.'
      );
      return;
    }

    const formData =
      new FormData();

    files.forEach((file) =>
      formData.append(
        'files',
        file
      )
    );

    setBusy(true);

    try {
      await request(
        `/student/assignments/${assignment.id}/submit`,
        {
          method: 'POST',
          body: formData,
        }
      );

      toast.success(
        'Assignment submitted'
      );

      onDone();
    } catch (error) {
      errorToast(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-head">
          <div>
            <h2>
              {assignment.title}
            </h2>

            <p>
              Due{' '}
              {dateText(
                assignment.due_date
              )}
            </p>
          </div>

          <button onClick={onClose}>
            <XMarkIcon />
          </button>
        </div>

        <div className="modal-body">
          <p>
            {assignment.description}
          </p>

          <h4>Submission</h4>

          <input
            type="file"
            multiple
            onChange={(event) =>
              setFiles([
                ...event.target.files,
              ])
            }
          />

          <small>
            Allowed:{' '}
            {(
              assignment.allowed_extensions ||
              []
            ).join(', ') ||
              'Configured by administrator'}
            {' · '}
            Max{' '}
            {assignment.max_file_size_mb ||
              50}{' '}
            MB
          </small>
        </div>

        <div className="modal-actions">
          <Button
            onClick={submit}
            disabled={busy}
          >
            {busy
              ? 'Uploading…'
              : 'Submit assignment'}
          </Button>

          <Button
            variant="outline"
            onClick={onClose}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

function StudentQuizzes() {
  const {
    domains,
    loading: domainLoading,
  } = useDomains();

  const [domainId, setDomainId] =
    useState('');

  const [items, setItems] =
    useState([]);

  const [loading, setLoading] =
    useState(false);

  const [attempt, setAttempt] =
    useState(null);

  useEffect(() => {
    if (
      !domainId &&
      domains.length
    ) {
      setDomainId(
        String(domains[0].id)
      );
    }
  }, [domains, domainId]);

  useEffect(() => {
    if (!domainId) {
      setItems([]);
      return;
    }

    setLoading(true);

    request(
      `/student/quizzes?domain_id=${domainId}`
    )
      .then(setItems)
      .catch(errorToast)
      .finally(() =>
        setLoading(false)
      );
  }, [domainId]);

  if (domainLoading) {
    return <Loading />;
  }

  if (attempt) {
    return (
      <QuizAttempt
        quiz={attempt}
        onBack={() =>
          setAttempt(null)
        }
      />
    );
  }

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ASSESSMENTS"
        title="Quizzes"
        subtitle="Attempt published quizzes for your assigned domains."
        action={
          <DomainPicker
            domains={domains}
            value={domainId}
            onChange={(id) =>
              setDomainId(
                String(id)
              )
            }
          />
        }
      />

      {loading ? (
        <Loading />
      ) : items.length ? (
        <div className="quiz-grid">
          {items.map((quiz) => (
            <article
              className="quiz-card"
              key={quiz.id}
            >
              <div className="quiz-icon">
                <QuestionMarkCircleIcon />
              </div>

              <Badge
                tone={
                  quiz.can_attempt
                    ? 'green'
                    : 'gray'
                }
              >
                {quiz.can_attempt
                  ? 'Available'
                  : 'Attempts complete'}
              </Badge>

              <h3>
                {quiz.title}
              </h3>

              <p>
                {quiz.description ||
                  'Quiz assessment'}
              </p>

              <div className="meta-line">
                <span>
                  {quiz.total_marks}{' '}
                  marks
                </span>

                <span>
                  Pass{' '}
                  {quiz.passing_score}%
                </span>
              </div>

              <Button
                disabled={
                  !quiz.can_attempt
                }
                onClick={async () => {
                  try {
                    const data =
                      await request(
                        `/student/quizzes/${quiz.id}/start`,
                        {
                          method:
                            'POST',
                        }
                      );

                    setAttempt(data);
                  } catch (error) {
                    errorToast(error);
                  }
                }}
              >
                Start quiz
              </Button>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={QuestionMarkCircleIcon}
          title="No quizzes yet"
          text="Published quizzes will appear here after your administrator adds them."
        />
      )}
    </>
  );
}

function QuizAttempt({
  quiz,
  onBack,
}) {
  const [answers, setAnswers] =
    useState({});

  const [busy, setBusy] =
    useState(false);

  const submit = async () => {
    setBusy(true);

    try {
      const payload =
        quiz.questions.map(
          (question) => ({
            question_id:
              question.id,

            selected_option_ids:
              answers[question.id]
                ? [
                    answers[
                      question.id
                    ],
                  ]
                : [],
          })
        );

      const result =
        await request(
          `/student/quizzes/${quiz.quiz_id}/attempts/${quiz.attempt_id}/submit`,
          {
            method: 'POST',
            body: JSON.stringify(
              payload
            ),
          }
        );

      toast.success(
        `Score: ${result.percentage.toFixed(
          1
        )}%`
      );

      onBack();
    } catch (error) {
      errorToast(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <PageTitle
        eyebrow="QODEKRAFT / QUIZ"
        title="Quiz attempt"
        subtitle={`${quiz.questions.length} questions · ${
          quiz.time_limit_minutes ||
          'No'
        } minute limit`}
        action={
          <Button
            variant="outline"
            onClick={onBack}
          >
            Exit
          </Button>
        }
      />

      <div className="quiz-attempt">
        {quiz.questions.map(
          (question, index) => (
            <article
              className="question"
              key={question.id}
            >
              <div className="question-no">
                {index + 1}
              </div>

              <div>
                <h3>
                  {
                    question.question_text
                  }
                </h3>

                {question.options.map(
                  (option) => (
                    <label
                      className="option"
                      key={option.id}
                    >
                      <input
                        type="radio"
                        name={`q-${question.id}`}
                        checked={
                          answers[
                            question.id
                          ] === option.id
                        }
                        onChange={() =>
                          setAnswers(
                            (previous) => ({
                              ...previous,
                              [question.id]:
                                option.id,
                            })
                          )
                        }
                      />

                      <span>
                        {
                          option.option_text
                        }
                      </span>
                    </label>
                  )
                )}
              </div>
            </article>
          )
        )}

        <Button
          onClick={submit}
          disabled={busy}
          icon={CheckCircleIcon}
        >
          {busy
            ? 'Submitting…'
            : 'Submit quiz'}
        </Button>
      </div>
    </section>
  );
}

function StudentProgress() {
  const [data, setData] =
    useState(null);

  useEffect(() => {
    request('/student/progress')
      .then(setData)
      .catch(errorToast);
  }, []);

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / PROGRESS"
        title="My Progress"
        subtitle="Your learning progress is calculated from backend activity."
      />

      {data ? (
        <>
          <section className="progress-hero">
            <div>
              <span>
                Overall completion
              </span>

              <strong>
                {data.overall_percentage ??
                  0}
                %
              </strong>
            </div>

            <Progress
              value={
                data.overall_percentage ||
                0
              }
            />
          </section>

          <div className="stats-grid">
            <Stat
              icon={VideoCameraIcon}
              label="Recordings completed"
              value={`${data.recordings?.completed || 0}/${data.recordings?.total || 0}`}
            />

            <Stat
              icon={QuestionMarkCircleIcon}
              label="Quizzes passed"
              value={`${data.quizzes?.passed || 0}/${data.quizzes?.total || 0}`}
              tone="violet"
            />

            <Stat
              icon={DocumentTextIcon}
              label="Assignments submitted"
              value={`${data.assignments?.submitted || 0}/${data.assignments?.total || 0}`}
              tone="green"
            />

            <Stat
              icon={FolderIcon}
              label="Projects submitted"
              value={`${data.projects?.submitted || 0}/${data.projects?.total || 0}`}
              tone="amber"
            />
          </div>

          <section className="panel">
            <h2>
              Domain progress
            </h2>

            {data.domains?.length ? (
              data.domains.map(
                (domain) => (
                  <div
                    className="progress-row"
                    key={domain.domain_id}
                  >
                    <div>
                      <strong>
                        {domain.domain_name}
                      </strong>

                      <span>
                        {domain.percentage}
                        % complete
                      </span>
                    </div>

                    <Progress
                      value={
                        domain.percentage
                      }
                    />
                  </div>
                )
              )
            ) : (
              <EmptyState
                icon={AcademicCapIcon}
                title="No domain progress"
                text="Progress will appear after your administrator assigns a domain."
              />
            )}
          </section>
        </>
      ) : (
        <Loading />
      )}
    </>
  );
}

function StudentProjects() {
  const {
    domains,
    loading: domainLoading,
  } = useDomains();

  const [items, setItems] =
    useState([]);

  const [domainId, setDomainId] =
    useState('');

  const [selected, setSelected] =
    useState(null);

  useEffect(() => {
    if (
      !domainId &&
      domains.length
    ) {
      setDomainId(
        String(domains[0].id)
      );
    }
  }, [domains, domainId]);

  useEffect(() => {
    if (!domainId) {
      setItems([]);
      return;
    }

    request(
      `/student/projects?domain_id=${domainId}`
    )
      .then(setItems)
      .catch(errorToast);
  }, [domainId]);

  if (domainLoading) {
    return <Loading />;
  }

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / PROJECTS"
        title="Projects"
        subtitle="Practical projects assigned to your learning domain."
        action={
          <DomainPicker
            domains={domains}
            value={domainId}
            onChange={(id) =>
              setDomainId(
                String(id)
              )
            }
          />
        }
      />

      {items.length ? (
        <div className="cards-list">
          {items.map((project) => (
            <article
              className="content-card"
              key={project.id}
            >
              <div className="card-icon">
                <FolderIcon />
              </div>

              <div className="card-main">
                <div className="card-line">
                  <h3>
                    {project.title}
                  </h3>

                  <Badge
                    tone={
                      project.submission
                        ? 'green'
                        : 'amber'
                    }
                  >
                    {project.submission
                      ?.status ||
                      'Not submitted'}
                  </Badge>
                </div>

                <p>
                  {project.description ||
                    'Project brief'}
                </p>

                <div className="meta-line">
                  <span>
                    Due{' '}
                    {dateText(
                      project.due_date
                    )}
                  </span>

                  <span>
                    {project.max_marks ??
                      '—'}{' '}
                    marks
                  </span>
                </div>
              </div>

              <Button
                variant="outline"
                onClick={() =>
                  setSelected(project)
                }
              >
                Open
              </Button>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={FolderIcon}
          title="No projects yet"
          text="Projects will appear here when your administrator publishes them."
        />
      )}

      {selected && (
        <ProjectModal
          project={selected}
          onClose={() =>
            setSelected(null)
          }
          onDone={() => {
            setSelected(null);

            request(
              `/student/projects?domain_id=${domainId}`
            )
              .then(setItems)
              .catch(() => {});
          }}
        />
      )}
    </>
  );
}

function ProjectModal({
  project,
  onClose,
  onDone,
}) {
  const [description, setDescription] =
    useState('');

  const [github, setGithub] =
    useState('');

  const [live, setLive] =
    useState('');

  const [files, setFiles] =
    useState([]);

  const [busy, setBusy] =
    useState(false);

  const submit = async () => {
    setBusy(true);

    try {
      const formData = new FormData();
      formData.append('description', description);
      formData.append('github_link', github);
      formData.append('live_demo_link', live);
      files.forEach((file) => formData.append('files', file));

      await request(
        `/student/projects/${project.id}/submit`,
        {
          method: 'POST',
          body: formData,
        }
      );

      toast.success(
        'Project submitted'
      );

      onDone();
    } catch (error) {
      errorToast(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-head">
          <div>
            <h2>
              {project.title}
            </h2>

            <p>
              Due{' '}
              {dateText(
                project.due_date
              )}
            </p>
          </div>

          <button onClick={onClose}>
            <XMarkIcon />
          </button>
        </div>

        <div className="modal-body">
          <p>
            {project.description}
          </p>

          {project.requirements && (
            <div className="brief">
              <strong>
                Requirements
              </strong>

              <p>
                {project.requirements}
              </p>
            </div>
          )}

          <Field label="Submission description">
            <textarea
              value={description}
              onChange={(event) =>
                setDescription(
                  event.target.value
                )
              }
              placeholder="Describe your implementation…"
            />
          </Field>

          <Field label="GitHub link">
            <input
              value={github}
              onChange={(event) =>
                setGithub(
                  event.target.value
                )
              }
              placeholder="https://github.com/…"
            />
          </Field>

          <Field label="Live demo link">
            <input
              value={live}
              onChange={(event) =>
                setLive(
                  event.target.value
                )
              }
              placeholder="https://…"
            />
          </Field>

          <Field label="Project files">
            <input
              type="file"
              multiple
              onChange={(event) =>
                setFiles(Array.from(event.target.files || []))
              }
            />
            <small>Upload ZIP, PDF, DOCX, images or supporting files.</small>
          </Field>
        </div>

        <div className="modal-actions">
          <Button
            onClick={submit}
            disabled={busy}
          >
            {busy
              ? 'Submitting…'
              : 'Submit project'}
          </Button>

          <Button
            variant="outline"
            onClick={onClose}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

function StudentAnnouncements() {
  const [items, setItems] =
    useState([]);

  useEffect(() => {
    request('/student/announcements')
      .then(setItems)
      .catch(errorToast);
  }, []);

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / UPDATES"
        title="Announcements"
        subtitle="Updates published for your account and assigned domains."
      />

      {items.length ? (
        <div className="announcement-page">
          {items.map(
            (announcement) => (
              <article
                className="announcement-card"
                key={announcement.id}
              >
                <div className="announcement-head">
                  <MegaphoneIcon />

                  <Badge>
                    {announcement.type}
                  </Badge>
                </div>

                <h2>
                  {announcement.title}
                </h2>

                <p>
                  {announcement.content}
                </p>

                <small>
                  Published{' '}
                  {dateText(
                    announcement.published_at ||
                      announcement.created_at
                  )}
                </small>
              </article>
            )
          )}
        </div>
      ) : (
        <EmptyState
          icon={MegaphoneIcon}
          title="No announcements"
          text="There are no published announcements for your account yet."
        />
      )}
    </>
  );
}

function Profile({ session }) {
  const [data, setData] =
    useState(null);

  const [passwords, setPasswords] =
    useState({
      current_password: '',
      new_password: '',
      confirm_password: '',
    });

  useEffect(() => {
    request('/auth/me')
      .then(setData)
      .catch(errorToast);
  }, []);

  const change = async (event) => {
    event.preventDefault();

    try {
      await request(
        '/auth/change-password',
        {
          method: 'POST',
          body: JSON.stringify(
            passwords
          ),
        }
      );

      toast.success(
        'Password changed'
      );

      setPasswords({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });
    } catch (error) {
      errorToast(error);
    }
  };

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ACCOUNT"
        title="Profile"
        subtitle="Your account details and security settings."
      />

      <div className="two-col">
        <section className="panel profile-card">
          <div className="profile-large">
            {(
              data?.full_name ||
              session.full_name ||
              'U'
            )
              .slice(0, 1)
              .toUpperCase()}
          </div>

          <h2>
            {data?.full_name ||
              session.full_name ||
              'User'}
          </h2>

          <p>
            {data?.email ||
              session.email}
          </p>

          <Badge tone="green">
            {data?.status ||
              session.status}
          </Badge>

          <div className="profile-details">
            <div>
              <span>Role</span>

              <strong>
                {data?.role ||
                  session.role}
              </strong>
            </div>

            <div>
              <span>
                Qualification
              </span>

              <strong>
                {data?.qualification ||
                  '—'}
              </strong>
            </div>

            <div>
              <span>
                Preferred domain
              </span>

              <strong>
                {data?.preferred_domain ||
                  '—'}
              </strong>
            </div>
          </div>
        </section>

        <section className="panel">
          <h2>
            Change password
          </h2>

          <p className="muted">
            Use a strong password with the
            minimum requirements enforced by
            the backend.
          </p>

          <form onSubmit={change}>
            <Field label="Current password">
              <input
                type="password"
                value={
                  passwords.current_password
                }
                onChange={(event) =>
                  setPasswords(
                    (previous) => ({
                      ...previous,
                      current_password:
                        event.target
                          .value,
                    })
                  )
                }
                required
              />
            </Field>

            <Field label="New password">
              <input
                type="password"
                value={
                  passwords.new_password
                }
                onChange={(event) =>
                  setPasswords(
                    (previous) => ({
                      ...previous,
                      new_password:
                        event.target
                          .value,
                    })
                  )
                }
                required
              />
            </Field>

            <Field label="Confirm new password">
              <input
                type="password"
                value={
                  passwords.confirm_password
                }
                onChange={(event) =>
                  setPasswords(
                    (previous) => ({
                      ...previous,
                      confirm_password:
                        event.target
                          .value,
                    })
                  )
                }
                required
              />
            </Field>

            <Button type="submit">
              Update password
            </Button>
          </form>
        </section>
      </div>
    </>
  );
}

/* =========================================================
   ADMIN
   ========================================================= */

function AdminPage({ page }) {
  if (page === 'Dashboard') {
    return <AdminDashboard />;
  }

  if (page === 'Students') {
    return (
      <AdminStudents
        approvalOnly={false}
      />
    );
  }

  if (page === 'Approval Requests') {
    return (
      <AdminStudents
        approvalOnly
      />
    );
  }

  if (page === 'Domains') {
    return <AdminDomains />;
  }

  if (page === 'Recordings') {
    return <AdminRecordings />;
  }

  if (page === 'Assignments') {
    return <AdminAssignments />;
  }

  if (page === 'Quizzes') {
    return <AdminQuizzes />;
  }

  if (page === 'Projects') {
    return <AdminProjects />;
  }


  if (page === 'Announcements') {
    return <AdminAnnouncements />;
  }

  if (page === 'Reports') {
    return <AdminReports />;
  }

  if (page === 'Platform Settings') {
    return <AdminSettings />;
  }

  if (page === 'Manage Admins') {
    return <AdminAdmins />;
  }

  return <EmptyState />;
}

function AdminDashboard() {
  const [data, setData] =
    useState(null);

  useEffect(() => {
    request('/admin/dashboard/stats')
      .then(setData)
      .catch(errorToast);
  }, []);

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Dashboard"
        subtitle="Live platform metrics from the connected database."
      />

      {data ? (
        <>
          <div className="stats-grid five">
            <Stat
              icon={UsersIcon}
              label="Students"
              value={
                data.students?.total ||
                0
              }
            />

            <Stat
              icon={CheckCircleIcon}
              label="Approved"
              value={
                data.students?.approved ||
                0
              }
              tone="green"
            />

            <Stat
              icon={ClockIcon}
              label="Pending"
              value={
                data.students?.pending ||
                0
              }
              tone="amber"
            />

            <Stat
              icon={AcademicCapIcon}
              label="Active domains"
              value={
                data.domains?.active ||
                0
              }
              tone="violet"
            />

            <Stat
              icon={VideoCameraIcon}
              label="Recordings"
              value={
                data.content?.recordings ||
                0
              }
            />
          </div>

          <div className="two-col">
            <section className="panel">
              <h2>
                Content inventory
              </h2>

              <div className="inventory">
                <div>
                  <span>
                    Assignments
                  </span>

                  <strong>
                    {data.content
                      ?.assignments || 0}
                  </strong>
                </div>

                <div>
                  <span>
                    Quizzes
                  </span>

                  <strong>
                    {data.content?.quizzes ||
                      0}
                  </strong>
                </div>

                <div>
                  <span>
                    Projects
                  </span>

                  <strong>
                    {data.content?.projects ||
                      0}
                  </strong>
                </div>
              </div>
            </section>

            <section className="panel">
              <h2>
                Recent registrations
              </h2>

              {data
                .recent_registrations
                ?.length ? (
                data.recent_registrations.map(
                  (user) => (
                    <div
                      className="simple-row"
                      key={user.id}
                    >
                      <UsersIcon />

                      <div>
                        <strong>
                          {user.full_name ||
                            'Unnamed student'}
                        </strong>

                        <small>
                          {user.email} ·{' '}
                          {user.status}
                        </small>
                      </div>
                    </div>
                  )
                )
              ) : (
                <EmptyState
                  icon={UsersIcon}
                  title="No registrations"
                  text="New student registrations will appear here."
                />
              )}
            </section>
          </div>
        </>
      ) : (
        <Loading />
      )}
    </>
  );
}

function AdminStudents({
  approvalOnly,
}) {
  const [rows, setRows] =
    useState([]);

  const [domains, setDomains] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [search, setSearch] =
    useState('');

  const [selected, setSelected] =
    useState(null);

  const load = () => {
    setLoading(true);

    const params =
      new URLSearchParams({
        page: '1',
        page_size: '100',
      });

    if (approvalOnly) {
      params.set(
        'status',
        'pending'
      );
    }

    if (search) {
      params.set(
        'search',
        search
      );
    }

    Promise.all([
      request(
        `/admin/students?${params}`
      ),
      request('/admin/domains'),
    ])
      .then(([studentData, domainData]) => {
        setRows(
          studentData.students || []
        );

        setDomains(
          domainData || []
        );
      })
      .catch(errorToast)
      .finally(() =>
        setLoading(false)
      );
  };

  useEffect(() => {
    load();
  }, [approvalOnly]);

  const act = async (
    id,
    action
  ) => {
    try {
      await request(
        `/admin/students/${id}/${action}`,
        {
          method: 'PATCH',
        }
      );

      toast.success(
        `Student ${action}`
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const deleteStudent = async (student) => {
    const name = student.full_name || student.email || `Student #${student.id}`;
    const confirmed = window.confirm(
      `Permanently delete ${name}?\n\nThis removes the student account, profile, domain access, submissions, quiz attempts, video progress, notifications and student-owned uploaded files. This cannot be undone.`
    );
    if (!confirmed) return;

    try {
      await request(`/admin/students/${student.id}`, { method: 'DELETE' });
      toast.success('Student permanently deleted');
      if (selected?.id === student.id) setSelected(null);
      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const assign = async (
    studentId,
    domainId
  ) => {
    if (!domainId) return;

    try {
      await request(
        `/admin/students/${studentId}/domains/${domainId}`,
        {
          method: 'POST',
        }
      );

      toast.success(
        'Domain assigned'
      );
    } catch (error) {
      errorToast(error);
    }
  };

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title={
          approvalOnly
            ? 'Approval Requests'
            : 'Students'
        }
        subtitle="Real student records loaded from your backend database."
      />

      <section className="panel">
        <div className="table-tools">
          <div className="search-field">
            <MagnifyingGlassIcon />

            <input
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value
                )
              }
              placeholder="Search name, email or phone"
              onKeyDown={(event) =>
                event.key ===
                  'Enter' &&
                load()
              }
            />
          </div>

          <Button
            variant="outline"
            onClick={load}
            icon={ArrowPathIcon}
          >
            Refresh
          </Button>
        </div>

        {loading ? (
          <Loading />
        ) : rows.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>
                    Domain access
                  </th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {rows.map((student) => (
                  <tr
                    key={student.id}
                  >
                    <td>
                      <strong>
                        {student.full_name ||
                          'Unnamed'}
                      </strong>
                    </td>

                    <td>
                      {student.email}
                      {student.preferred_domain && (
                        <small style={{ display: 'block', marginTop: 4 }}>Requested: {student.preferred_domain}</small>
                      )}
                    </td>

                    <td>
                      <Badge
                        tone={
                          student.status ===
                          'approved'
                            ? 'green'
                            : student.status ===
                                'pending'
                              ? 'amber'
                              : 'red'
                        }
                      >
                        {student.status}
                      </Badge>
                    </td>

                    <td>
                      {dateText(
                        student.created_at
                      )}
                    </td>

                    <td>
                      <select
                        defaultValue=""
                        onChange={(event) =>
                          assign(
                            student.id,
                            event.target
                              .value
                          )
                        }
                      >
                        <option value="">
                          Assign domain…
                        </option>

                        {domains.map(
                          (domain) => (
                            <option
                              key={
                                domain.id
                              }
                              value={
                                domain.id
                              }
                            >
                              {
                                domain.name
                              }
                            </option>
                          )
                        )}
                      </select>
                    </td>

                    <td>
                      <div className="actions">
                        {student.status ===
                          'pending' && (
                          <Button
                            variant="small"
                            onClick={() =>
                              act(
                                student.id,
                                'approve'
                              )
                            }
                          >
                            Approve
                          </Button>
                        )}

                        {student.status ===
                          'approved' && (
                          <Button
                            variant="small danger-btn"
                            onClick={() =>
                              act(
                                student.id,
                                'suspend'
                              )
                            }
                          >
                            Suspend
                          </Button>
                        )}

                        {student.status ===
                          'blocked' && (
                          <Button
                            variant="small"
                            onClick={() =>
                              act(
                                student.id,
                                'unblock'
                              )
                            }
                          >
                            Unblock
                          </Button>
                        )}

                        {student.status !==
                          'blocked' &&
                          student.status !==
                            'pending' && (
                            <Button
                              variant="small danger-btn"
                              onClick={() =>
                                act(
                                  student.id,
                                  'block'
                                )
                              }
                            >
                              Block
                            </Button>
                          )}

                        <button
                          className="icon-action"
                          onClick={() =>
                            setSelected(
                              student
                            )
                          }
                          title="View"
                        >
                          <EyeIcon />
                        </button>

                        <button
                          className="icon-action danger"
                          onClick={() => deleteStudent(student)}
                          title="Permanently delete student"
                        >
                          <TrashIcon />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={UsersIcon}
            title={
              approvalOnly
                ? 'No pending approvals'
                : 'No students'
            }
            text={
              approvalOnly
                ? 'There are no student accounts waiting for approval.'
                : 'Student registrations will appear here when accounts are created.'
            }
          />
        )}
      </section>

      {selected && (
        <StudentDetail
          student={selected}
          domains={domains}
          onClose={() =>
            setSelected(null)
          }
          onRefresh={load}
        />
      )}
    </>
  );
}

function StudentDetail({
  student,
  domains,
  onClose,
  onRefresh,
}) {
  const [detail, setDetail] =
    useState(student);
  const [overview, setOverview] =
    useState(null);

  useEffect(() => {
    Promise.all([
      request(`/admin/students/${student.id}`),
      request(`/admin/students/${student.id}/overview`),
    ])
      .then(([profile, data]) => {
        setDetail(profile);
        setOverview(data);
      })
      .catch(errorToast);
  }, [student.id]);

  return (
    <div className="modal-backdrop">
      <div className="modal wide">
        <div className="modal-head">
          <div>
            <h2>
              {detail.full_name ||
                'Student'}
            </h2>

            <p>
              {detail.email}
            </p>
          </div>

          <button onClick={onClose}>
            <XMarkIcon />
          </button>
        </div>

        <div className="modal-body">
          <div className="detail-grid">
            <div>
              <span>Status</span>

              <strong>
                {detail.status}
              </strong>
            </div>

            <div>
              <span>Joined</span>

              <strong>
                {dateText(
                  detail.created_at
                )}
              </strong>
            </div>
          </div>

          {overview?.summary && (
            <>
              <h3>Student Overview</h3>
              <div className="detail-grid">
                <div><span>Assignment submissions</span><strong>{overview.summary.assignment_submissions}</strong></div>
                <div><span>Project submissions</span><strong>{overview.summary.project_submissions}</strong></div>
                <div><span>Quiz attempts</span><strong>{overview.summary.quiz_attempts}</strong></div>
                <div><span>Completed recordings</span><strong>{overview.summary.completed_recordings}</strong></div>
              </div>
            </>
          )}

          {overview?.assignment_submissions?.length > 0 && (
            <div className="stack-list">
              <h3>Assignment activity</h3>
              {overview.assignment_submissions.slice(0, 10).map((x) => (
                <div className="simple-row" key={`a-${x.id}`}>
                  <DocumentTextIcon /><div><strong>Assignment #{x.assignment_id}</strong><small>{x.status} · {x.marks_obtained ?? '—'} marks</small></div>
                </div>
              ))}
            </div>
          )}

          {overview?.project_submissions?.length > 0 && (
            <div className="stack-list">
              <h3>Project activity</h3>
              {overview.project_submissions.slice(0, 10).map((x) => (
                <div className="simple-row" key={`p-${x.id}`}>
                  <FolderIcon /><div><strong>Project #{x.project_id}</strong><small>{x.status} · {x.marks_obtained ?? '—'} marks</small></div></div>
              ))}
            </div>
          )}

          {overview?.quiz_attempts?.length > 0 && (
            <div className="stack-list">
              <h3>Quiz activity</h3>
              {overview.quiz_attempts.slice(0, 10).map((x) => (
                <div className="simple-row" key={`q-${x.id}`}>
                  <QuestionMarkCircleIcon /><div><strong>Quiz #{x.quiz_id} · Attempt {x.attempt_number}</strong><small>{x.percentage ?? 0}% · {x.is_passed ? 'Passed' : 'Not passed'}</small></div></div>
              ))}
            </div>
          )}

          <h3>
            Assigned domains
          </h3>

          {detail.domains?.length ? (
            detail.domains.map(
              (domain) => (
                <div
                  className="simple-row"
                  key={domain.id}
                >
                  <AcademicCapIcon />

                  <div>
                    <strong>
                      {
                        domain.domain_name
                      }
                    </strong>

                    <small>
                      {domain.status} ·
                      expires{' '}
                      {dateText(
                        domain.access_expires_at
                      )}
                    </small>
                  </div>
                </div>
              )
            )
          ) : (
            <p className="muted">
              No domain access assigned.
            </p>
          )}

          <h3>
            Assign another domain
          </h3>

          <select
            onChange={async (event) => {
              if (!event.target.value)
                return;

              try {
                await request(
                  `/admin/students/${detail.id}/domains/${event.target.value}`,
                  {
                    method: 'POST',
                  }
                );

                toast.success(
                  'Domain assigned'
                );

                const fresh =
                  await request(
                    `/admin/students/${detail.id}`
                  );

                setDetail(fresh);

                onRefresh();
              } catch (error) {
                errorToast(error);
              }
            }}
          >
            <option value="">
              Select domain
            </option>

            {domains.map(
              (domain) => (
                <option
                  key={domain.id}
                  value={domain.id}
                >
                  {domain.name}
                </option>
              )
            )}
          </select>
        </div>
      </div>
    </div>
  );
}

function AdminDomains() {
  const [items, setItems] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [form, setForm] =
    useState({
      name: '',
      description: '',
      duration_weeks: '',
      max_active_recordings: 45,
      recording_retention_days: 15,
    });

  const load = () => {
    setLoading(true);

    request('/admin/domains')
      .then(setItems)
      .catch(errorToast)
      .finally(() =>
        setLoading(false)
      );
  };

  useEffect(() => {
    load();
  }, []);

  const create = async (event) => {
    event.preventDefault();

    const formData =
      new FormData();

    Object.entries(form).forEach(
      ([key, value]) => {
        if (value !== '') {
          formData.append(
            key,
            value
          );
        }
      }
    );

    try {
      await request(
        '/admin/domains',
        {
          method: 'POST',
          body: formData,
        }
      );

      toast.success(
        'Domain created'
      );

      setForm({
        name: '',
        description: '',
        duration_weeks: '',
        max_active_recordings: 45,
        recording_retention_days: 15,
      });

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const toggle = async (id) => {
    try {
      await request(
        `/admin/domains/${id}/toggle-active`,
        {
          method: 'PATCH',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const del = async (id) => {
    if (
      !confirm(
        'Delete this domain?'
      )
    ) {
      return;
    }

    try {
      await request(
        `/admin/domains/${id}`,
        {
          method: 'DELETE',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Learning Domains"
        subtitle="Create the domains that administrators can assign to students."
      />

      <div className="two-col">
        <section className="panel">
          <h2>
            Create domain
          </h2>

          <form onSubmit={create}>
            <Field label="Domain name *">
              <input
                required
                value={form.name}
                onChange={(event) =>
                  setForm({
                    ...form,
                    name: event.target
                      .value,
                  })
                }
                placeholder="Data Science"
              />
            </Field>

            <Field label="Description">
              <textarea
                value={
                  form.description
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    description:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <div className="form-grid">
              <Field label="Duration (weeks)">
                <input
                  type="number"
                  value={
                    form.duration_weeks
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      duration_weeks:
                        event.target
                          .value,
                    })
                  }
                />
              </Field>

              <Field label="Max active recordings">
                <input
                  type="number"
                  value={
                    form.max_active_recordings
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      max_active_recordings:
                        event.target
                          .value,
                    })
                  }
                />
              </Field>
            </div>

            <Field label="Recording retention (days)">
              <input
                type="number"
                value={
                  form.recording_retention_days
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    recording_retention_days:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <Button icon={PlusIcon}>
              Create domain
            </Button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Domains</h2>

            <Button
              variant="outline"
              onClick={load}
              icon={ArrowPathIcon}
            >
              Refresh
            </Button>
          </div>

          {loading ? (
            <Loading />
          ) : items.length ? (
            <div className="stack-list">
              {items.map(
                (domain) => (
                  <div
                    className="manage-row"
                    key={domain.id}
                  >
                    <div className="row-icon">
                      <AcademicCapIcon />
                    </div>

                    <div className="row-main">
                      <strong>
                        {domain.name}
                      </strong>

                      <small>
                        {domain.description ||
                          'No description'}{' '}
                        ·{' '}
                        {domain.duration_weeks ||
                          '—'}{' '}
                        weeks
                      </small>
                    </div>

                    <Badge
                      tone={
                        domain.is_active
                          ? 'green'
                          : 'gray'
                      }
                    >
                      {domain.is_active
                        ? 'Active'
                        : 'Inactive'}
                    </Badge>

                    <button
                      className="icon-action"
                      onClick={() =>
                        toggle(
                          domain.id
                        )
                      }
                      title="Toggle"
                    >
                      <ArrowPathIcon />
                    </button>

                    <button
                      className="icon-action danger"
                      onClick={() =>
                        del(
                          domain.id
                        )
                      }
                      title="Delete"
                    >
                      <TrashIcon />
                    </button>
                  </div>
                )
              )}
            </div>
          ) : (
            <EmptyState
              icon={AcademicCapIcon}
              title="No domains created"
              text="Create the first learning domain."
            />
          )}
        </section>
      </div>
    </>
  );
}

function AdminRecordings() {
  const [domains, setDomains] =
    useState([]);

  const [items, setItems] =
    useState([]);
  const [reviewing, setReviewing] =
    useState(null);

  const [form, setForm] =
    useState({
      domain_id: '',
      title: '',
      description: '',
      topic: '',
      class_number: '',
      duration_seconds: '',
      is_published: false,
    });

  const [video, setVideo] =
    useState(null);

  const [thumb, setThumb] =
    useState(null);

  const load = () =>
    Promise.all([
      request('/admin/domains'),
      request(
        '/admin/recordings?page=1&page_size=100'
      ),
    ])
      .then(
        ([domainData, recordingData]) => {
          setDomains(
            domainData
          );

          setItems(
            recordingData.recordings ||
              []
          );
        }
      )
      .catch(errorToast);

  useEffect(() => {
    load();
  }, []);

  const create = async (event) => {
    event.preventDefault();

    if (!video) {
      toast.error(
        'Select a video file.'
      );

      return;
    }

    const formData =
      new FormData();

    Object.entries(form).forEach(
      ([key, value]) =>
        formData.append(
          key,
          value
        )
    );

    formData.append(
      'video',
      video
    );

    if (thumb) {
      formData.append(
        'thumbnail',
        thumb
      );
    }

    try {
      await request(
        '/admin/recordings',
        {
          method: 'POST',
          body: formData,
        }
      );

      toast.success(
        'Recording uploaded'
      );

      setVideo(null);

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const publish = async (
    recording
  ) => {
    try {
      await request(
        `/admin/recordings/${recording.id}/${recording.is_published ? 'unpublish' : 'publish'}`,
        {
          method: 'PATCH',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const del = async (id) => {
    if (
      !confirm(
        'Delete recording and its media?'
      )
    ) {
      return;
    }

    try {
      await request(
        `/admin/recordings/${id}`,
        {
          method: 'DELETE',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Recorded Classes"
        subtitle="Upload, publish and manage protected learning videos."
      />

      <div className="two-col">
        <section className="panel">
          <h2>
            Upload recording
          </h2>

          <form onSubmit={create}>
            <Field label="Domain *">
              <select
                required
                value={form.domain_id}
                onChange={(event) =>
                  setForm({
                    ...form,
                    domain_id:
                      event.target
                        .value,
                  })
                }
              >
                <option value="">
                  Select domain
                </option>

                {domains.map(
                  (domain) => (
                    <option
                      key={domain.id}
                      value={domain.id}
                    >
                      {domain.name}
                    </option>
                  )
                )}
              </select>
            </Field>

            <Field label="Title *">
              <input
                required
                value={form.title}
                onChange={(event) =>
                  setForm({
                    ...form,
                    title: event.target
                      .value,
                  })
                }
              />
            </Field>

            <Field label="Description">
              <textarea
                value={
                  form.description
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    description:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <div className="form-grid">
              <Field label="Topic">
                <input
                  value={form.topic}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      topic: event.target
                        .value,
                    })
                  }
                />
              </Field>

              <Field label="Class number">
                <input
                  type="number"
                  value={
                    form.class_number
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      class_number:
                        event.target
                          .value,
                    })
                  }
                />
              </Field>
            </div>

            <Field label="Duration (seconds)">
              <input
                type="number"
                value={
                  form.duration_seconds
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    duration_seconds:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <Field label="Video *">
              <input
                type="file"
                accept="video/*"
                required
                onChange={(event) =>
                  setVideo(
                    event.target
                      .files?.[0] ||
                      null
                  )
                }
              />
            </Field>

            <Field label="Thumbnail">
              <input
                type="file"
                accept="image/*"
                onChange={(event) =>
                  setThumb(
                    event.target
                      .files?.[0] ||
                      null
                  )
                }
              />
            </Field>

            <label className="check">
              <input
                type="checkbox"
                checked={
                  form.is_published
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    is_published:
                      event.target
                        .checked,
                  })
                }
              />

              Publish immediately
            </label>

            <Button icon={PlusIcon}>
              Upload recording
            </Button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>
              Published & draft
              recordings
            </h2>

            <Button
              variant="outline"
              onClick={load}
              icon={ArrowPathIcon}
            >
              Refresh
            </Button>
          </div>

          {items.length ? (
            <div className="stack-list">
              {items.map(
                (recording) => (
                  <div
                    className="manage-row"
                    key={recording.id}
                  >
                    <div className="row-icon">
                      <VideoCameraIcon />
                    </div>

                    <div className="row-main">
                      <strong>
                        {recording.title}
                      </strong>

                      <small>
                        Class{' '}
                        {recording.class_number ||
                          '—'}{' '}
                        ·{' '}
                        {recording.video_name ||
                          'No video file'}
                      </small>
                    </div>

                    <Badge
                      tone={
                        recording.is_published
                          ? 'green'
                          : 'gray'
                      }
                    >
                      {recording.is_published
                        ? 'Published'
                        : 'Draft'}
                    </Badge>

                    <button
                      className="icon-action"
                      onClick={() =>
                        publish(
                          recording
                        )
                      }
                      title="Publish/unpublish"
                    >
                      <ArrowPathIcon />
                    </button>

                    <button
                      className="icon-action danger"
                      onClick={() =>
                        del(
                          recording.id
                        )
                      }
                    >
                      <TrashIcon />
                    </button>
                  </div>
                )
              )}
            </div>
          ) : (
            <EmptyState
              icon={VideoCameraIcon}
              title="No recordings"
              text="Upload your first class recording."
            />
          )}
        </section>
      </div>
    </>
  );
}

function AdminAssignments() {
  const [domains, setDomains] =
    useState([]);

  const [items, setItems] =
    useState([]);

  const [reviewing, setReviewing] =
    useState(null);

  const [form, setForm] =
    useState({
      domain_id: '',
      title: '',
      description: '',
      instructions: '',
      topic: '',
      due_date: '',
      max_marks: 100,
      allowed_extensions:
        '["pdf","zip","docx"]',
      max_file_size_mb: 50,
      is_published: false,
    });

  const load = () =>
    Promise.all([
      request('/admin/domains'),
      request(
        '/admin/assignments?page=1&page_size=100'
      ),
    ])
      .then(
        ([domainData, assignmentData]) => {
          setDomains(
            domainData
          );

          setItems(
            assignmentData.assignments ||
              []
          );
        }
      )
      .catch(errorToast);

  useEffect(() => {
    load();
  }, []);

  const create = async (event) => {
    event.preventDefault();

    const formData =
      new FormData();

    Object.entries(form).forEach(
      ([key, value]) =>
        formData.append(
          key,
          value
        )
    );

    try {
      await request(
        '/admin/assignments',
        {
          method: 'POST',
          body: formData,
        }
      );

      toast.success(
        'Assignment created'
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const publish = async (id) => {
    try {
      await request(
        `/admin/assignments/${id}/publish`,
        {
          method: 'PATCH',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const del = async (id) => {
    if (
      !confirm(
        'Delete assignment?'
      )
    ) {
      return;
    }

    try {
      await request(
        `/admin/assignments/${id}`,
        {
          method: 'DELETE',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Assignments"
        subtitle="Create assignments and review student submissions."
      />

      <div className="two-col">
        <section className="panel">
          <h2>
            Create assignment
          </h2>

          <form onSubmit={create}>
            <Field label="Domain *">
              <select
                required
                value={form.domain_id}
                onChange={(event) =>
                  setForm({
                    ...form,
                    domain_id:
                      event.target
                        .value,
                  })
                }
              >
                <option value="">
                  Select domain
                </option>

                {domains.map(
                  (domain) => (
                    <option
                      key={domain.id}
                      value={domain.id}
                    >
                      {domain.name}
                    </option>
                  )
                )}
              </select>
            </Field>

            <Field label="Title *">
              <input
                required
                value={form.title}
                onChange={(event) =>
                  setForm({
                    ...form,
                    title: event.target
                      .value,
                  })
                }
              />
            </Field>

            <Field label="Description">
              <textarea
                value={
                  form.description
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    description:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <Field label="Instructions">
              <textarea
                value={
                  form.instructions
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    instructions:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <div className="form-grid">
              <Field label="Due date">
                <input
                  type="datetime-local"
                  value={
                    form.due_date
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      due_date:
                        event.target
                          .value,
                    })
                  }
                />
              </Field>

              <Field label="Max marks">
                <input
                  type="number"
                  value={
                    form.max_marks
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      max_marks:
                        event.target
                          .value,
                    })
                  }
                />
              </Field>
            </div>

            <Field label="Allowed extensions (JSON)">
              <input
                value={
                  form.allowed_extensions
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    allowed_extensions:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <Button icon={PlusIcon}>
              Create assignment
            </Button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>
              Assignments
            </h2>

            <Button
              variant="outline"
              onClick={load}
              icon={ArrowPathIcon}
            >
              Refresh
            </Button>
          </div>

          {items.length ? (
            <div className="stack-list">
              {items.map(
                (assignment) => (
                  <div
                    className="manage-row"
                    key={assignment.id}
                  >
                    <div className="row-icon">
                      <DocumentTextIcon />
                    </div>

                    <div className="row-main">
                      <strong>
                        {assignment.title}
                      </strong>

                      <small>
                        {dateText(
                          assignment.due_date
                        )}{' '}
                        ·{' '}
                        {assignment.max_marks}{' '}
                        marks
                      </small>
                    </div>

                    <Badge
                      tone={
                        assignment.is_published
                          ? 'green'
                          : 'gray'
                      }
                    >
                      {assignment.is_published
                        ? 'Published'
                        : 'Draft'}
                    </Badge>

                    {!assignment.is_published && (
                      <button
                        className="icon-action"
                        onClick={() =>
                          publish(
                            assignment.id
                          )
                        }
                      >
                        <CheckCircleIcon />
                      </button>
                    )}

                    <Button
                      variant="small outline"
                      onClick={() => setReviewing(assignment)}
                    >
                      Review submissions
                    </Button>

                    <button
                      className="icon-action danger"
                      onClick={() =>
                        del(
                          assignment.id
                        )
                      }
                    >
                      <TrashIcon />
                    </button>
                  </div>
                )
              )}
            </div>
          ) : (
            <EmptyState
              icon={DocumentTextIcon}
              title="No assignments"
              text="Create the first assignment."
            />
          )}
        </section>
      </div>
      {reviewing && <SubmissionReviewModal type="assignment" item={reviewing} onClose={() => setReviewing(null)} />}
    </>
  );
}

function SubmissionReviewModal({ type, item, onClose }) {
  const [submissions, setSubmissions] = useState([]);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = () => {
    const base = type === 'assignment' ? '/admin/assignments' : '/admin/projects';
    request(`${base}/${item.id}/submissions`).then(setSubmissions).catch(errorToast);
  };
  useEffect(() => { load(); }, [item.id, type]);

  const review = async () => {
    if (!editing) return;
    setBusy(true);
    try {
      const base = type === 'assignment' ? '/admin/assignments' : '/admin/projects';
      const params = new URLSearchParams({
        status: editing.status || 'reviewed',
        marks_obtained: editing.marks_obtained ?? '',
        feedback: editing.feedback || '',
        correction_request: editing.correction_request || '',
      });
      await request(`${base}/${item.id}/submissions/${editing.id}/review?${params}`, { method: 'PATCH' });
      toast.success('Submission reviewed');
      setEditing(null);
      load();
    } catch (error) { errorToast(error); } finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal wide">
        <div className="modal-head"><div><h2>Review {type} submissions</h2><p>{item.title}</p></div><button onClick={onClose}><XMarkIcon /></button></div>
        <div className="modal-body">
          {submissions.length ? submissions.map((sub) => (
            <div className="panel" key={sub.id} style={{ marginBottom: 12 }}>
              <div className="card-line"><strong>{sub.student_name || `Student #${sub.student_id}`}</strong><small>{sub.student_email || ''}</small><Badge tone={sub.status === 'approved' ? 'green' : 'amber'}>{sub.status}</Badge></div>
              {type === 'project' && <><p>{sub.description || 'No description'}</p><p>GitHub: {sub.github_link ? <a href={sub.github_link} target="_blank" rel="noreferrer">{sub.github_link}</a> : '—'}<br/>Live demo: {sub.live_demo_link ? <a href={sub.live_demo_link} target="_blank" rel="noreferrer">{sub.live_demo_link}</a> : '—'}</p></>}
              {sub.files?.length > 0 && <div className="stack"><strong>Uploaded files</strong>{sub.files.map((f) => <button className="link-button" key={f.id} onClick={() => downloadProtectedFile(`/admin/${type === 'assignment' ? 'assignments' : 'projects'}/${item.id}/submissions/${sub.id}/files/${f.id}`, f.original_name || f.file_name).catch(errorToast)}>{f.original_name || f.file_name}</button>)}</div>}
              <div className="form-grid">
                <Field label="Status"><select value={editing?.id === sub.id ? editing.status : sub.status} onChange={(e) => setEditing({...sub, status: e.target.value})}><option value="under_review">Under review</option><option value="reviewed">Reviewed</option><option value="returned">Returned</option><option value="approved">Approved</option><option value="rejected">Rejected</option></select></Field>
                <Field label="Marks"><input type="number" value={editing?.id === sub.id ? (editing.marks_obtained ?? '') : (sub.marks_obtained ?? '')} onChange={(e) => setEditing({...sub, marks_obtained: e.target.value})}/></Field>
              </div>
              <Field label="Feedback"><textarea value={editing?.id === sub.id ? (editing.feedback || '') : (sub.feedback || '')} onChange={(e) => setEditing({...sub, feedback: e.target.value})}/></Field>
              {type === 'assignment' && <Field label="Correction request"><textarea value={editing?.id === sub.id ? (editing.correction_request || '') : (sub.correction_request || '')} onChange={(e) => setEditing({...sub, correction_request: e.target.value})}/></Field>}
              <Button onClick={() => { setEditing({...sub}); }} disabled={busy}>{editing?.id === sub.id ? 'Editing submission' : 'Select for review'}</Button>{editing?.id === sub.id && <Button variant="outline" onClick={review} disabled={busy}>Save review</Button>}
            </div>
          )) : <EmptyState icon={DocumentTextIcon} title="No submissions" text="Students have not submitted this work yet."/>}
        </div>
        <div className="modal-actions"><Button variant="outline" onClick={onClose}>Close</Button></div>
      </div>
    </div>
  );
}


function AdminQuizzes() {
  const emptyQuestion = () => ({
    id: null,
    question_text: '',
    question_type: 'single_choice',
    marks: 1,
    explanation: '',
    order_index: 0,
    options: [
      { option_text: '', is_correct: false },
      { option_text: '', is_correct: false },
      { option_text: '', is_correct: false },
      { option_text: '', is_correct: false },
    ],
  });

  const [domains, setDomains] = useState([]);
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({
    domain_id: '',
    title: '',
    description: '',
    time_limit_minutes: 15,
    max_attempts: 1,
    passing_score: 60,
    total_marks: 10,
    due_date: '',
    is_published: false,
  });

  const [questionQuiz, setQuestionQuiz] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [questionLoading, setQuestionLoading] = useState(false);
  const [questionBusy, setQuestionBusy] = useState(false);
  const [questionForm, setQuestionForm] = useState(emptyQuestion());

  const load = () =>
    Promise.all([
      request('/admin/domains'),
      request('/admin/quizzes'),
    ])
      .then(([domainData, quizData]) => {
        setDomains(domainData);
        setItems(quizData);
      })
      .catch(errorToast);

  useEffect(() => {
    load();
  }, []);

  const create = async (event) => {
    event.preventDefault();

    if (!form.domain_id) {
      toast.error('Please select a domain.');
      return;
    }

    try {
      await request('/admin/quizzes', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          domain_id: Number(form.domain_id),
          time_limit_minutes: Number(form.time_limit_minutes),
          max_attempts: Number(form.max_attempts),
          passing_score: Number(form.passing_score),
          total_marks: Number(form.total_marks),
          due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
        }),
      });

      toast.success('Quiz created');

      setForm({
        domain_id: '',
        title: '',
        description: '',
        time_limit_minutes: 15,
        max_attempts: 1,
        passing_score: 60,
        total_marks: 10,
        due_date: '',
        is_published: false,
      });

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const toggle = async (quiz) => {
    if (!quiz.is_published && Number(quiz.question_count || 0) < 1) {
      toast.error('Add at least one question before publishing this quiz.');
      return;
    }

    try {
      await request(
        `/admin/quizzes/${quiz.id}/${quiz.is_published ? 'unpublish' : 'publish'}`,
        { method: 'PATCH' }
      );

      toast.success(
        quiz.is_published ? 'Quiz unpublished' : 'Quiz published'
      );
      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const del = async (id) => {
    if (!confirm('Delete quiz? All questions and attempts for this quiz will also be removed.')) {
      return;
    }

    try {
      await request(`/admin/quizzes/${id}`, { method: 'DELETE' });
      toast.success('Quiz deleted');
      load();

      if (questionQuiz?.id === id) {
        setQuestionQuiz(null);
        setQuestions([]);
      }
    } catch (error) {
      errorToast(error);
    }
  };

  const openQuestionManager = async (quiz) => {
    setQuestionQuiz(quiz);
    setQuestionLoading(true);
    setQuestionForm(emptyQuestion());

    try {
      const data = await request(`/admin/quizzes/${quiz.id}`);
      setQuestions(data.questions || []);
      setQuestionQuiz({ ...quiz, ...data });
    } catch (error) {
      errorToast(error);
      setQuestionQuiz(null);
    } finally {
      setQuestionLoading(false);
    }
  };

  const closeQuestionManager = () => {
    setQuestionQuiz(null);
    setQuestions([]);
    setQuestionForm(emptyQuestion());
  };

  const updateOption = (index, key, value) => {
    setQuestionForm((previous) => {
      const options = previous.options.map((option, optionIndex) => {
        if (optionIndex !== index) return option;

        if (key === 'is_correct' && previous.question_type === 'single_choice' && value) {
          return { ...option, is_correct: true };
        }

        return { ...option, [key]: value };
      });

      if (key === 'is_correct' && previous.question_type === 'single_choice' && value) {
        return {
          ...previous,
          options: options.map((option, optionIndex) => ({
            ...option,
            is_correct: optionIndex === index,
          })),
        };
      }

      return { ...previous, options };
    });
  };

  const changeQuestionType = (type) => {
    setQuestionForm((previous) => {
      const options = previous.options.map((option, index) => ({
        ...option,
        is_correct: type === 'single_choice' ? index === 0 : option.is_correct,
      }));

      return {
        ...previous,
        question_type: type,
        options,
      };
    });
  };

  const saveQuestion = async (event) => {
    event.preventDefault();

    const questionText = questionForm.question_text.trim();
    if (!questionText) {
      toast.error('Enter the question text.');
      return;
    }

    const cleanedOptions = questionForm.options.map((option) => ({
      option_text: option.option_text.trim(),
      is_correct: Boolean(option.is_correct),
    }));

    if (cleanedOptions.some((option) => !option.option_text)) {
      toast.error('Please fill all four options.');
      return;
    }

    const correctCount = cleanedOptions.filter((option) => option.is_correct).length;

    if (correctCount === 0) {
      toast.error('Select the correct answer.');
      return;
    }

    if (questionForm.question_type === 'single_choice' && correctCount !== 1) {
      toast.error('Single-choice questions must have exactly one correct answer.');
      return;
    }

    if (Number(questionForm.marks) <= 0) {
      toast.error('Marks must be greater than 0.');
      return;
    }

    if (!questionQuiz) return;

    setQuestionBusy(true);

    try {
      const payload = {
        question_text: questionText,
        question_type: questionForm.question_type,
        marks: Number(questionForm.marks),
        explanation: questionForm.explanation.trim() || null,
        order_index: Number(questionForm.order_index || questions.length),
        options: cleanedOptions,
      };

      let saved;

      if (questionForm.id) {
        saved = await request(
          `/admin/quizzes/${questionQuiz.id}/questions/${questionForm.id}`,
          {
            method: 'PUT',
            body: JSON.stringify(payload),
          }
        );

        setQuestions((previous) =>
          previous.map((question) =>
            question.id === questionForm.id ? saved : question
          )
        );

        toast.success('Question updated');
      } else {
        saved = await request(
          `/admin/quizzes/${questionQuiz.id}/questions`,
          {
            method: 'POST',
            body: JSON.stringify(payload),
          }
        );

        setQuestions((previous) => [...previous, saved]);
        toast.success('Question added');
      }

      setQuestionForm(emptyQuestion());

      const quizData = await request(`/admin/quizzes/${questionQuiz.id}`);
      setQuestionQuiz({ ...questionQuiz, ...quizData });
      setItems((previous) =>
        previous.map((quiz) =>
          quiz.id === questionQuiz.id ? { ...quiz, ...quizData } : quiz
        )
      );
    } catch (error) {
      errorToast(error);
    } finally {
      setQuestionBusy(false);
    }
  };

  const editQuestion = (question) => {
    const options = Array.from({ length: 4 }, (_, index) =>
      question.options?.[index]
        ? {
            option_text: question.options[index].option_text || '',
            is_correct: Boolean(question.options[index].is_correct),
          }
        : {
            option_text: '',
            is_correct: false,
          }
    );

    setQuestionForm({
      id: question.id,
      question_text: question.question_text || '',
      question_type: question.question_type || 'single_choice',
      marks: question.marks ?? 1,
      explanation: question.explanation || '',
      order_index: question.order_index ?? questions.length,
      options,
    });

    window.setTimeout(() => {
      document
        .getElementById('qk-question-form')
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 0);
  };

  const deleteQuestion = async (question) => {
    if (!confirm('Delete this question?')) return;

    try {
      await request(
        `/admin/quizzes/${questionQuiz.id}/questions/${question.id}`,
        { method: 'DELETE' }
      );

      setQuestions((previous) =>
        previous.filter((item) => item.id !== question.id)
      );

      setQuestionForm(emptyQuestion());

      const quizData = await request(`/admin/quizzes/${questionQuiz.id}`);
      setQuestionQuiz({ ...questionQuiz, ...quizData });
      setItems((previous) =>
        previous.map((quiz) =>
          quiz.id === questionQuiz.id ? { ...quiz, ...quizData } : quiz
        )
      );

      toast.success('Question deleted');
    } catch (error) {
      errorToast(error);
    }
  };

  const resetQuestion = () => {
    setQuestionForm(emptyQuestion());
  };

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Quizzes"
        subtitle="Create quizzes, add questions and options, edit question banks, and publish assessments."
      />

      <div className="two-col">
        <section className="panel">
          <h2>Create quiz</h2>

          <form onSubmit={create}>
            <Field label="Domain *">
              <select
                required
                value={form.domain_id}
                onChange={(event) =>
                  setForm({
                    ...form,
                    domain_id: event.target.value,
                  })
                }
              >
                <option value="">Select domain</option>

                {domains.map((domain) => (
                  <option key={domain.id} value={domain.id}>
                    {domain.name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Title *">
              <input
                required
                value={form.title}
                onChange={(event) =>
                  setForm({
                    ...form,
                    title: event.target.value,
                  })
                }
                placeholder="e.g. Python Fundamentals Quiz"
              />
            </Field>

            <Field label="Description">
              <textarea
                value={form.description}
                onChange={(event) =>
                  setForm({
                    ...form,
                    description: event.target.value,
                  })
                }
                placeholder="Short description for students"
              />
            </Field>

            <div className="form-grid">
              <Field label="Time limit (minutes)">
                <input
                  type="number"
                  min="1"
                  value={form.time_limit_minutes}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      time_limit_minutes: event.target.value,
                    })
                  }
                />
              </Field>

              <Field label="Max attempts">
                <input
                  type="number"
                  min="1"
                  value={form.max_attempts}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      max_attempts: event.target.value,
                    })
                  }
                />
              </Field>
            </div>

            <div className="form-grid">
              <Field label="Passing score %">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={form.passing_score}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      passing_score: event.target.value,
                    })
                  }
                />
              </Field>

              <Field label="Total marks">
                <input
                  type="number"
                  min="1"
                  value={form.total_marks}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      total_marks: event.target.value,
                    })
                  }
                />
              </Field>
            </div>

            <Field label="Deadline">
              <input
                type="datetime-local"
                value={form.due_date}
                onChange={(event) => setForm({ ...form, due_date: event.target.value })}
              />
            </Field>

            <Button icon={PlusIcon}>Create quiz</Button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Quiz library</h2>
              <p>Create a quiz first, then use <b>Questions</b> to add its question and options.</p>
            </div>

            <Button
              variant="outline"
              onClick={load}
              icon={ArrowPathIcon}
            >
              Refresh
            </Button>
          </div>

          {items.length ? (
            <div className="stack-list">
              {items.map((quiz) => (
                <div className="manage-row" key={quiz.id}>
                  <div className="row-icon">
                    <QuestionMarkCircleIcon />
                  </div>

                  <div className="row-main">
                    <strong>{quiz.title}</strong>

                    <small>
                      {quiz.question_count || 0} questions · {quiz.total_marks} marks{quiz.due_date ? ` · Due ${new Date(quiz.due_date).toLocaleString()}` : ''}
                    </small>
                  </div>

                  <Badge
                    tone={quiz.is_published ? 'green' : 'gray'}
                  >
                    {quiz.is_published ? 'Published' : 'Draft'}
                  </Badge>

                  <button
                    className="icon-action"
                    title="Manage questions"
                    onClick={() => openQuestionManager(quiz)}
                  >
                    <PencilSquareIcon />
                  </button>

                  <button
                    className="icon-action"
                    title={quiz.is_published ? 'Unpublish quiz' : 'Publish quiz'}
                    onClick={() => toggle(quiz)}
                  >
                    {quiz.is_published ? <EyeIcon /> : <ArrowPathIcon />}
                  </button>

                  <button
                    className="icon-action danger"
                    title="Delete quiz"
                    onClick={() => del(quiz.id)}
                  >
                    <TrashIcon />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={QuestionMarkCircleIcon}
              title="No quizzes"
              text="Create a quiz and then add questions from its question manager."
            />
          )}
        </section>
      </div>

      {questionQuiz && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '980px', width: '96%' }}>
            <div className="modal-head">
              <div>
                <h2>Question Manager</h2>
                <p>
                  {questionQuiz.title} · {questions.length} question
                  {questions.length === 1 ? '' : 's'}
                </p>
              </div>

              <button onClick={closeQuestionManager} title="Close">
                <XMarkIcon />
              </button>
            </div>

            <div className="modal-body">
              {questionLoading ? (
                <Loading />
              ) : (
                <>
                  <section
                    id="qk-question-form"
                    className="panel"
                    style={{ marginBottom: '20px' }}
                  >
                    <div className="panel-head">
                      <div>
                        <h3>
                          {questionForm.id ? 'Edit question' : 'Add question'}
                        </h3>
                        <p>
                          Enter the question, four options, correct answer, marks and explanation.
                        </p>
                      </div>

                      {questionForm.id && (
                        <Button
                          variant="outline"
                          type="button"
                          onClick={resetQuestion}
                        >
                          Cancel edit
                        </Button>
                      )}
                    </div>

                    <form onSubmit={saveQuestion}>
                      <Field label="Question *">
                        <textarea
                          required
                          value={questionForm.question_text}
                          onChange={(event) =>
                            setQuestionForm({
                              ...questionForm,
                              question_text: event.target.value,
                            })
                          }
                          placeholder="Type the question here..."
                          rows={4}
                        />
                      </Field>

                      <div className="form-grid">
                        <Field label="Question type">
                          <select
                            value={questionForm.question_type}
                            onChange={(event) =>
                              changeQuestionType(event.target.value)
                            }
                          >
                            <option value="single_choice">
                              Single choice
                            </option>
                            <option value="multiple_choice">
                              Multiple choice
                            </option>
                          </select>
                        </Field>

                        <Field label="Marks *">
                          <input
                            type="number"
                            min="0.1"
                            step="0.1"
                            required
                            value={questionForm.marks}
                            onChange={(event) =>
                              setQuestionForm({
                                ...questionForm,
                                marks: event.target.value,
                              })
                            }
                          />
                        </Field>
                      </div>

                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr',
                          gap: '12px',
                          marginTop: '8px',
                        }}
                      >
                        <Field
                          label={
                            questionForm.question_type === 'single_choice'
                              ? 'Options — select one correct answer *'
                              : 'Options — select all correct answers *'
                          }
                        >
                          <div style={{ display: 'grid', gap: '10px' }}>
                            {questionForm.options.map((option, index) => (
                              <div
                                key={index}
                                style={{
                                  display: 'grid',
                                  gridTemplateColumns: 'auto 1fr',
                                  alignItems: 'center',
                                  gap: '10px',
                                }}
                              >
                                <input
                                  type={
                                    questionForm.question_type === 'single_choice'
                                      ? 'radio'
                                      : 'checkbox'
                                  }
                                  name="correct-answer"
                                  checked={Boolean(option.is_correct)}
                                  onChange={(event) =>
                                    updateOption(
                                      index,
                                      'is_correct',
                                      event.target.checked
                                    )
                                  }
                                  title="Mark as correct answer"
                                />

                                <input
                                  value={option.option_text}
                                  onChange={(event) =>
                                    updateOption(
                                      index,
                                      'option_text',
                                      event.target.value
                                    )
                                  }
                                  placeholder={`Option ${String.fromCharCode(65 + index)}`}
                                  required
                                />
                              </div>
                            ))}
                          </div>
                        </Field>
                      </div>

                      <Field label="Explanation">
                        <textarea
                          value={questionForm.explanation}
                          onChange={(event) =>
                            setQuestionForm({
                              ...questionForm,
                              explanation: event.target.value,
                            })
                          }
                          placeholder="Explain why the correct answer is right (optional)"
                          rows={3}
                        />
                      </Field>

                      <div
                        style={{
                          display: 'flex',
                          gap: '10px',
                          flexWrap: 'wrap',
                          alignItems: 'center',
                        }}
                      >
                        <Button
                          type="submit"
                          disabled={questionBusy}
                          icon={questionForm.id ? PencilSquareIcon : PlusIcon}
                        >
                          {questionBusy
                            ? 'Saving…'
                            : questionForm.id
                              ? 'Update question'
                              : 'Add question'}
                        </Button>

                        <Button
                          type="button"
                          variant="outline"
                          onClick={resetQuestion}
                          disabled={questionBusy}
                        >
                          Clear
                        </Button>
                      </div>
                    </form>
                  </section>

                  <section className="panel">
                    <div className="panel-head">
                      <div>
                        <h3>Questions in this quiz</h3>
                        <p>
                          {questions.length
                            ? 'Edit or delete any question below.'
                            : 'No questions have been added yet.'}
                        </p>
                      </div>

                      <Badge tone={questions.length ? 'green' : 'amber'}>
                        {questions.length} added
                      </Badge>
                    </div>

                    {questions.length ? (
                      <div className="stack-list">
                        {questions.map((question, index) => (
                          <div
                            className="manage-row"
                            key={question.id}
                            style={{
                              alignItems: 'flex-start',
                              padding: '16px',
                            }}
                          >
                            <div className="row-icon">
                              <span>{index + 1}</span>
                            </div>

                            <div
                              className="row-main"
                              style={{ minWidth: 0 }}
                            >
                              <strong>
                                {question.question_text}
                              </strong>

                              <small>
                                {question.options?.length || 0} options ·{' '}
                                {question.marks} mark
                                {Number(question.marks) === 1 ? '' : 's'} ·{' '}
                                {question.question_type === 'multiple_choice'
                                  ? 'Multiple choice'
                                  : 'Single choice'}
                              </small>

                              <div
                                style={{
                                  display: 'grid',
                                  gap: '5px',
                                  marginTop: '8px',
                                }}
                              >
                                {(question.options || []).map((option, optionIndex) => (
                                  <div key={option.id || optionIndex}>
                                    <span
                                      style={{
                                        fontWeight: option.is_correct ? 700 : 400,
                                      }}
                                    >
                                      {String.fromCharCode(65 + optionIndex)}.{' '}
                                      {option.option_text}
                                      {option.is_correct ? ' ✓' : ''}
                                    </span>
                                  </div>
                                ))}
                              </div>

                              {question.explanation && (
                                <small style={{ marginTop: '8px' }}>
                                  Explanation: {question.explanation}
                                </small>
                              )}
                            </div>

                            <button
                              className="icon-action"
                              title="Edit question"
                              onClick={() => editQuestion(question)}
                            >
                              <PencilSquareIcon />
                            </button>

                            <button
                              className="icon-action danger"
                              title="Delete question"
                              onClick={() => deleteQuestion(question)}
                            >
                              <TrashIcon />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <EmptyState
                        icon={QuestionMarkCircleIcon}
                        title="No questions yet"
                        text="Use the form above to add the first question and its four options."
                      />
                    )}
                  </section>
                </>
              )}
            </div>

            <div className="modal-actions">
              <Button
                variant="outline"
                onClick={closeQuestionManager}
              >
                Close
              </Button>

              <Button
                disabled={!questions.length}
                onClick={() => {
                  closeQuestionManager();
                  load();
                }}
              >
                Done
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function AdminProjects() {
  const [domains, setDomains] =
    useState([]);

  const [items, setItems] =
    useState([]);
  const [reviewing, setReviewing] =
    useState(null);

  const [form, setForm] =
    useState({
      domain_id: '',
      title: '',
      description: '',
      requirements: '',
      technologies: '',
      due_date: '',
      max_marks: 100,
      submission_instructions: '',
      is_published: false,
    });

  const load = () =>
    Promise.all([
      request('/admin/domains'),
      request('/admin/projects'),
    ])
      .then(
        ([domainData, projectData]) => {
          setDomains(
            domainData
          );

          setItems(
            projectData
          );
        }
      )
      .catch(errorToast);

  useEffect(() => {
    load();
  }, []);

  const create = async (event) => {
    event.preventDefault();

    try {
      await request(
        '/admin/projects',
        {
          method: 'POST',
          body: JSON.stringify({
            ...form,
            domain_id:
              Number(
                form.domain_id
              ),
            technologies:
              form.technologies
                .split(',')
                .map((item) =>
                  item.trim()
                )
                .filter(Boolean),
            max_marks:
              Number(
                form.max_marks
              ),
          }),
        }
      );

      toast.success(
        'Project created'
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const toggle = async (
    project
  ) => {
    try {
      await request(
        `/admin/projects/${project.id}/${project.is_published ? 'unpublish' : 'publish'}`,
        {
          method: 'PATCH',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const del = async (id) => {
    if (
      !confirm(
        'Delete project?'
      )
    ) {
      return;
    }

    try {
      await request(
        `/admin/projects/${id}`,
        {
          method: 'DELETE',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Projects"
        subtitle="Create practical projects and publish them to assigned domains."
      />

      <div className="two-col">
        <section className="panel">
          <h2>
            Create project
          </h2>

          <form onSubmit={create}>
            <Field label="Domain *">
              <select
                required
                value={form.domain_id}
                onChange={(event) =>
                  setForm({
                    ...form,
                    domain_id:
                      event.target
                        .value,
                  })
                }
              >
                <option value="">
                  Select domain
                </option>

                {domains.map(
                  (domain) => (
                    <option
                      key={domain.id}
                      value={domain.id}
                    >
                      {domain.name}
                    </option>
                  )
                )}
              </select>
            </Field>

            <Field label="Title *">
              <input
                required
                value={form.title}
                onChange={(event) =>
                  setForm({
                    ...form,
                    title: event.target
                      .value,
                  })
                }
              />
            </Field>

            <Field label="Description">
              <textarea
                value={
                  form.description
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    description:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <Field label="Requirements">
              <textarea
                value={
                  form.requirements
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    requirements:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <Field label="Technologies (comma separated)">
              <input
                value={
                  form.technologies
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    technologies:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <div className="form-grid">
              <Field label="Due date">
                <input
                  type="datetime-local"
                  value={
                    form.due_date
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      due_date:
                        event.target
                          .value,
                    })
                  }
                />
              </Field>

              <Field label="Max marks">
                <input
                  type="number"
                  value={
                    form.max_marks
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      max_marks:
                        event.target
                          .value,
                    })
                  }
                />
              </Field>
            </div>

            <Field label="Submission instructions">
              <textarea
                value={
                  form.submission_instructions
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    submission_instructions:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <Button icon={PlusIcon}>
              Create project
            </Button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>
              Project library
            </h2>

            <Button
              variant="outline"
              onClick={load}
              icon={ArrowPathIcon}
            >
              Refresh
            </Button>
          </div>

          {items.length ? (
            <div className="stack-list">
              {items.map(
                (project) => (
                  <div
                    className="manage-row"
                    key={project.id}
                  >
                    <div className="row-icon">
                      <FolderIcon />
                    </div>

                    <div className="row-main">
                      <strong>
                        {project.title}
                      </strong>

                      <small>
                        {project.max_marks}{' '}
                        marks ·{' '}
                        {dateText(
                          project.due_date
                        )}
                      </small>
                    </div>

                    <Badge
                      tone={
                        project.is_published
                          ? 'green'
                          : 'gray'
                      }
                    >
                      {project.is_published
                        ? 'Published'
                        : 'Draft'}
                    </Badge>

                    <button
                      className="icon-action"
                      onClick={() =>
                        toggle(
                          project
                        )
                      }
                    >
                      <ArrowPathIcon />
                    </button>

                    <Button variant="small outline" onClick={() => setReviewing(project)}>Review submissions</Button>

                    <button
                      className="icon-action danger"
                      onClick={() =>
                        del(
                          project.id
                        )
                      }
                    >
                      <TrashIcon />
                    </button>
                  </div>
                )
              )}
            </div>
          ) : (
            <EmptyState
              icon={FolderIcon}
              title="No projects"
              text="Create the first project."
            />
          )}
        </section>
      </div>
      {reviewing && <SubmissionReviewModal type="project" item={reviewing} onClose={() => setReviewing(null)} />}
    </>
  );
}

function AdminAnnouncements() {
  const [items, setItems] =
    useState([]);

  const [domains, setDomains] =
    useState([]);

  const [form, setForm] =
    useState({
      title: '',
      content: '',
      type: 'general',
      is_global: true,
      domain_id: '',
      is_published: true,
    });

  const load = () =>
    Promise.all([
      request(
        '/admin/announcements'
      ),
      request('/admin/domains'),
    ])
      .then(
        ([announcementData, domainData]) => {
          setItems(
            announcementData
          );

          setDomains(
            domainData
          );
        }
      )
      .catch(errorToast);

  useEffect(() => {
    load();
  }, []);

  const create = async (event) => {
    event.preventDefault();

    try {
      await request(
        '/admin/announcements',
        {
          method: 'POST',
          body: JSON.stringify({
            ...form,
            domain_id: form.is_global
              ? null
              : form.domain_id
                ? Number(
                    form.domain_id
                  )
                : null,
          }),
        }
      );

      toast.success(
        'Announcement published'
      );

      setForm({
        title: '',
        content: '',
        type: 'general',
        is_global: true,
        domain_id: '',
        is_published: true,
      });

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const toggle = async (id) => {
    try {
      await request(
        `/admin/announcements/${id}/toggle`,
        {
          method: 'PATCH',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  const del = async (id) => {
    if (
      !confirm(
        'Delete announcement?'
      )
    ) {
      return;
    }

    try {
      await request(
        `/admin/announcements/${id}`,
        {
          method: 'DELETE',
        }
      );

      load();
    } catch (error) {
      errorToast(error);
    }
  };

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Announcements"
        subtitle="Publish global or domain-specific updates."
      />

      <div className="two-col">
        <section className="panel">
          <h2>
            Create announcement
          </h2>

          <form onSubmit={create}>
            <Field label="Title *">
              <input
                required
                value={form.title}
                onChange={(event) =>
                  setForm({
                    ...form,
                    title: event.target
                      .value,
                  })
                }
              />
            </Field>

            <Field label="Content *">
              <textarea
                required
                rows="8"
                value={
                  form.content
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    content:
                      event.target
                        .value,
                  })
                }
              />
            </Field>

            <Field label="Type">
              <select
                value={form.type}
                onChange={(event) =>
                  setForm({
                    ...form,
                    type: event.target
                      .value,
                  })
                }
              >
                <option>
                  general
                </option>
                <option>
                  important
                </option>
                <option>
                  assignment
                </option>
                <option>
                  quiz
                </option>
                <option>
                  project
                </option>
                <option>
                  recording
                </option>
              </select>
            </Field>

            <label className="check">
              <input
                type="checkbox"
                checked={
                  form.is_global
                }
                onChange={(event) =>
                  setForm({
                    ...form,
                    is_global:
                      event.target
                        .checked,
                  })
                }
              />

              Global announcement
            </label>

            {!form.is_global && (
              <Field label="Domain">
                <select
                  value={
                    form.domain_id
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      domain_id:
                        event.target
                          .value,
                    })
                  }
                >
                  <option value="">
                    Select domain
                  </option>

                  {domains.map(
                    (domain) => (
                      <option
                        key={
                          domain.id
                        }
                        value={
                          domain.id
                        }
                      >
                        {domain.name}
                      </option>
                    )
                  )}
                </select>
              </Field>
            )}

            <Button
              icon={MegaphoneIcon}
            >
              Publish announcement
            </Button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>
              Announcement history
            </h2>

            <Button
              variant="outline"
              onClick={load}
              icon={ArrowPathIcon}
            >
              Refresh
            </Button>
          </div>

          {items.length ? (
            <div className="stack-list">
              {items.map(
                (announcement) => (
                  <div
                    className="manage-row"
                    key={
                      announcement.id
                    }
                  >
                    <div className="row-icon">
                      <MegaphoneIcon />
                    </div>

                    <div className="row-main">
                      <strong>
                        {
                          announcement.title
                        }
                      </strong>

                      <small>
                        {announcement.is_global
                          ? 'Global'
                          : 'Domain specific'}{' '}
                        ·{' '}
                        {dateText(
                          announcement.created_at
                        )}
                      </small>
                    </div>

                    <Badge
                      tone={
                        announcement.is_published
                          ? 'green'
                          : 'gray'
                      }
                    >
                      {announcement.is_published
                        ? 'Published'
                        : 'Hidden'}
                    </Badge>

                    <button
                      className="icon-action"
                      onClick={() =>
                        toggle(
                          announcement.id
                        )
                      }
                    >
                      <ArrowPathIcon />
                    </button>

                    <button
                      className="icon-action danger"
                      onClick={() =>
                        del(
                          announcement.id
                        )
                      }
                    >
                      <TrashIcon />
                    </button>
                  </div>
                )
              )}
            </div>
          ) : (
            <EmptyState
              icon={MegaphoneIcon}
              title="No announcements"
              text="Create your first announcement."
            />
          )}
        </section>
      </div>
    </>
  );
}

function AdminReports() {
  const [logs, setLogs] =
    useState([]);

  const [cleanup, setCleanup] =
    useState([]);

  const load = () =>
    Promise.all([
      request(
        '/admin/audit-logs?page=1&page_size=50'
      ),
      request(
        '/admin/cleanup/logs?page=1&page_size=20'
      ),
    ])
      .then(
        ([auditData, cleanupData]) => {
          setLogs(
            auditData.logs || []
          );

          setCleanup(
            cleanupData.logs || []
          );
        }
      )
      .catch(errorToast);

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Reports & Audit"
        subtitle="Operational records from the connected backend."
      />

      <div className="two-col">
        <section className="panel">
          <div className="panel-head">
            <h2>
              Audit log
            </h2>

            <Button
              variant="outline"
              onClick={load}
              icon={ArrowPathIcon}
            >
              Refresh
            </Button>
          </div>

          {logs.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Action</th>
                    <th>User</th>
                    <th>Status</th>
                    <th>Time</th>
                  </tr>
                </thead>

                <tbody>
                  {logs.map(
                    (log) => (
                      <tr
                        key={log.id}
                      >
                        <td>
                          {log.action}
                        </td>

                        <td>
                          {log.user_email ||
                            '—'}
                        </td>

                        <td>
                          {log.status}
                        </td>

                        <td>
                          {dateText(
                            log.created_at
                          )}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={ClockIcon}
              title="No audit events"
              text="Administrative actions will be recorded here."
            />
          )}
        </section>

        <section className="panel">
          <h2>
            Storage cleanup
          </h2>

          {cleanup.length ? (
            cleanup.map(
              (item) => (
                <div
                  className="simple-row"
                  key={item.id}
                >
                  <ArrowDownTrayIcon />

                  <div>
                    <strong>
                      {item.status}
                    </strong>

                    <small>
                      {
                        item.recordings_deleted
                      }{' '}
                      recordings deleted ·{' '}
                      {
                        item.assignments_deleted
                      }{' '}
                      assignments deleted
                    </small>
                  </div>
                </div>
              )
            )
          ) : (
            <EmptyState
              icon={ArrowDownTrayIcon}
              title="No cleanup runs"
              text="Scheduled or manual cleanup activity will appear here."
            />
          )}
        </section>
      </div>
    </>
  );
}

function AdminSettings() {
  const [data, setData] =
    useState(null);

  const [busy, setBusy] =
    useState(false);

  useEffect(() => {
    request('/admin/settings')
      .then(setData)
      .catch(errorToast);
  }, []);

  const save = async () => {
    if (!data) return;

    setBusy(true);

    try {
      const updates = {};

      Object.entries(data).forEach(
        ([key, item]) => {
          updates[key] = item.value;
        }
      );

      await request(
        '/admin/settings',
        {
          method: 'PATCH',
          body: JSON.stringify(
            updates
          ),
        }
      );

      toast.success(
        'Settings saved'
      );
    } catch (error) {
      errorToast(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Platform Settings"
        subtitle="Backend-managed security, retention and platform configuration."
      />

      {data ? (
        <section className="panel">
          <div className="settings-list">
            {Object.entries(data).map(
              ([key, item]) => (
                <label
                  className="setting-row"
                  key={key}
                >
                  <div>
                    <strong>
                      {key}
                    </strong>

                    <small>
                      {item.description ||
                        'System setting'}
                    </small>
                  </div>

                  <input
                    value={
                      item.value ?? ''
                    }
                    onChange={(event) =>
                      setData(
                        (previous) => ({
                          ...previous,
                          [key]: {
                            ...item,
                            value:
                              event.target
                                .value,
                          },
                        })
                      )
                    }
                  />
                </label>
              )
            )}
          </div>

          <Button
            onClick={save}
            disabled={busy}
          >
            {busy
              ? 'Saving…'
              : 'Save settings'}
          </Button>
        </section>
      ) : (
        <Loading />
      )}
    </>
  );
}

function AdminAdmins() {
  const [me, setMe] =
    useState(null);

  useEffect(() => {
    request('/auth/me')
      .then(setMe)
      .catch(errorToast);
  }, []);

  return (
    <>
      <PageTitle
        eyebrow="QODEKRAFT / ADMIN"
        title="Manage Admins"
        subtitle="Administrator access is managed through backend credentials."
      />

      <section className="panel">
        <div className="notice large">
          <ShieldCheckIcon />

          <div>
            <h2>
              Administrator access
            </h2>

            <p>
              There is intentionally no
              public admin signup. Create
              or rotate administrator
              credentials through the
              backend environment.
            </p>
          </div>
        </div>

        {me && (
          <div className="detail-grid">
            <div>
              <span>Email</span>

              <strong>
                {me.email}
              </strong>
            </div>

            <div>
              <span>Role</span>

              <strong>
                {me.role}
              </strong>
            </div>

            <div>
              <span>Status</span>

              <strong>
                {me.status}
              </strong>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

/* =========================================================
   SHARED PROGRESS COMPONENT
   ========================================================= */

function Progress({ value = 0 }) {
  const safeValue = Math.max(
    0,
    Math.min(100, Number(value) || 0)
  );

  return (
    <div className="progress">
      <div
        className="progress-bar"
        style={{
          width: `${safeValue}%`,
        }}
      />
    </div>
  );

}

export default App;

