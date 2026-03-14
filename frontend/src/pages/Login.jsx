import AuthPage from '../AuthPage';

export default function Login() {
  const token = localStorage.getItem('access_token');
  if (token) {
    window.location.replace('/dashboard');
    return null;
  }
  return <AuthPage />;
}
