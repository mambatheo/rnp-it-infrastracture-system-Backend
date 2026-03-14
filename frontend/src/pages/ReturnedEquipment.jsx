import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';


export default function ReturnedEquipment() {
  const navigate = useNavigate();
  useEffect(() => { navigate('/deployments', { replace: true }); }, [navigate]);
  return null;
}
