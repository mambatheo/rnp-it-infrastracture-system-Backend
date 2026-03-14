import { useAuth } from '../hooks/useAuth';


const CanAccess = ({ permission, children, fallback = null }) => {
  const { can } = useAuth();
  return can(permission) ? children : fallback;
};

export default CanAccess;