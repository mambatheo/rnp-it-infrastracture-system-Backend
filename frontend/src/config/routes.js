import { ROLES } from './permissions';

export const ROUTES = [
  {
    path: '/dashboard',
    label: 'Dashboard',
    icon: 'LayoutDashboard',
    roles: [ROLES.ADMIN, ROLES.IT_STAFF, ROLES.TECHNICIAN, ROLES.USER],
  },
  {
    path: '/users',
    label: 'Users',
    icon: 'Users',
    roles: [ROLES.ADMIN],
  },
  {
    path: '/equipment',
    label: 'Equipment',
    icon: 'Monitor',
    roles: [ROLES.ADMIN, ROLES.IT_STAFF],
  },
  {
    path: '/stock',
    label: 'Stock',
    icon: 'PackageCheck',
    roles: [ROLES.ADMIN, ROLES.IT_STAFF],
  },
  {
    path: '/my-equipment',
    label: 'My Equipment',
    icon: 'Laptop',
    roles: [ROLES.TECHNICIAN, ROLES.USER],
  },
  {
    path: '/deployments',
    label: 'Deployments',
    icon: 'Truck',
    roles: [ROLES.ADMIN, ROLES.IT_STAFF],
  },
  {
    path: '/maintenance',
    label: 'Maintenance',
    icon: 'Wrench',
    roles: [ROLES.ADMIN, ROLES.IT_STAFF, ROLES.TECHNICIAN],
  },
  {
    path: '/my-requests',
    label: 'My Requests',
    icon: 'ClipboardList',
    roles: [ROLES.USER],
  },
  {
    path: '/reports',
    label: 'Reports',
    icon: 'FileBarChart',
    roles: [ROLES.ADMIN, ROLES.IT_STAFF],
  },
  {
    path: '/settings',
    label: 'Settings',
    icon: 'Settings',
    roles: [ROLES.ADMIN],
  },
];