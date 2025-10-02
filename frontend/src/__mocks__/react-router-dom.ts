import React from 'react';

export const useLocation = () => ({
  pathname: '/test',
  search: '',
  hash: '',
  state: null,
  key: 'default'
});

export const useNavigate = () => () => {};

export const useParams = () => ({});

export const NavLink = ({ children, to, className, ...props }: any) => {
  const isActive = false;
  const computedClassName = typeof className === 'function' ? className({ isActive }) : className;
  return React.createElement('a', { href: to, className: computedClassName, ...props }, children);
};

export const Link = ({ children, to, ...props }: any) => {
  return React.createElement('a', { href: to, ...props }, children);
};

export const BrowserRouter = ({ children }: any) => children;
export const MemoryRouter = ({ children }: any) => children;
export const Routes = ({ children }: any) => children;
export const Route = () => null;
