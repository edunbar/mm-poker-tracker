import { X, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { updateUserProfile, updatePassword, deleteAccount } from '../api/auth';
import { PlayerIdentitiesSection } from '../components/PlayerIdentitiesSection';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../shared/ui/button';
import { FormField, FormLabel, FormMessage } from '../shared/ui/form-field';
import { Input } from '../shared/ui/input';
import { Heading, Text } from '../shared/ui/typography';

type PasswordStrength = 'weak' | 'medium' | 'strong';

export default function SettingsPage() {
  const navigate = useNavigate();
  const { user, updateUser, logout } = useAuth();
  const [displayName, setDisplayName] = useState(user?.displayName || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Change Password Modal State
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmNewPassword: '',
  });
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [isPasswordLoading, setIsPasswordLoading] = useState(false);

  // Delete Account Modal State
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteForm, setDeleteForm] = useState({
    password: '',
    confirmation: '',
  });
  const [showDeletePassword, setShowDeletePassword] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [isDeleteLoading, setIsDeleteLoading] = useState(false);

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Reset displayName when user changes (e.g., after login)
  useEffect(() => {
    if (user?.displayName) {
      setDisplayName(user.displayName);
    }
  }, [user?.displayName]);

  const handleCancel = () => {
    setDisplayName(user?.displayName || '');
    setError('');
    setSuccess(false);
  };

  // Password strength indicator (reused from RegisterPage)
  const getPasswordStrength = (pwd: string): PasswordStrength | null => {
    if (pwd.length === 0) return null;
    if (pwd.length < 12) return 'weak';
    if (pwd.length < 16) return 'medium';
    return 'strong';
  };

  const getStrengthColor = (strength: PasswordStrength | null) => {
    if (!strength) return '';
    switch (strength) {
      case 'weak':
        return 'text-red-600';
      case 'medium':
        return 'text-yellow-600';
      case 'strong':
        return 'text-green-600';
    }
  };

  const getStrengthLabel = (strength: PasswordStrength | null) => {
    if (!strength) return '';
    switch (strength) {
      case 'weak':
        return 'Weak';
      case 'medium':
        return 'Medium';
      case 'strong':
        return 'Strong';
    }
  };

  const passwordStrength = getPasswordStrength(passwordForm.newPassword);

  // Change Password Handlers
  const handleChangePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess(false);

    // Validation
    if (!passwordForm.currentPassword) {
      setPasswordError('Current password is required');
      return;
    }
    if (!passwordForm.newPassword) {
      setPasswordError('New password is required');
      return;
    }
    if (passwordForm.newPassword.length < 12) {
      setPasswordError('New password must be at least 12 characters');
      return;
    }
    if (passwordForm.newPassword.length > 72) {
      setPasswordError('New password must not exceed 72 characters');
      return;
    }
    if (passwordForm.newPassword !== passwordForm.confirmNewPassword) {
      setPasswordError('Passwords do not match');
      return;
    }
    if (passwordForm.currentPassword === passwordForm.newPassword) {
      setPasswordError('New password must be different from current password');
      return;
    }

    setIsPasswordLoading(true);

    try {
      await updatePassword(passwordForm.currentPassword, passwordForm.newPassword);
      setPasswordSuccess(true);
      setPasswordForm({
        currentPassword: '',
        newPassword: '',
        confirmNewPassword: '',
      });

      // Auto-clear success message after 3 seconds
      setTimeout(() => {
        setPasswordSuccess(false);
        setShowChangePassword(false);
      }, 3000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || 'Failed to update password. Please try again.';
      if (err.response?.status === 401) {
        setPasswordError('Current password is incorrect');
      } else {
        setPasswordError(errorMessage);
      }
    } finally {
      setIsPasswordLoading(false);
    }
  };

  const handleCloseChangePassword = () => {
    setShowChangePassword(false);
    setPasswordForm({
      currentPassword: '',
      newPassword: '',
      confirmNewPassword: '',
    });
    setPasswordError('');
    setPasswordSuccess(false);
    setShowCurrentPassword(false);
    setShowNewPassword(false);
    setShowConfirmPassword(false);
  };

  // Delete Account Handlers
  const handleDeleteAccountSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setDeleteError('');

    // Validation
    if (!deleteForm.password) {
      setDeleteError('Password is required');
      return;
    }
    if (deleteForm.confirmation !== 'DELETE') {
      setDeleteError('Please type DELETE to confirm');
      return;
    }

    setIsDeleteLoading(true);

    try {
      await deleteAccount(deleteForm.password, deleteForm.confirmation);
      // Logout and redirect
      logout();
      navigate('/', { replace: true });
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || 'Failed to delete account. Please try again.';
      if (err.response?.status === 401) {
        setDeleteError('Incorrect password');
      } else {
        setDeleteError(errorMessage);
      }
    } finally {
      setIsDeleteLoading(false);
    }
  };

  const handleCloseDeleteModal = () => {
    setShowDeleteModal(false);
    setDeleteForm({
      password: '',
      confirmation: '',
    });
    setDeleteError('');
    setShowDeletePassword(false);
  };

  const isDeleteButtonEnabled = deleteForm.password && deleteForm.confirmation === 'DELETE';

  const validateDisplayName = (name: string): string | null => {
    const trimmed = name.trim();

    if (!trimmed) {
      return 'Display name cannot be empty';
    }

    if (trimmed.length < 2) {
      return 'Display name must be at least 2 characters';
    }

    if (trimmed.length > 50) {
      return 'Display name must not exceed 50 characters';
    }

    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    const trimmedName = displayName.trim();

    // Check if unchanged
    if (trimmedName === user?.displayName) {
      return;
    }

    // Frontend validation
    const validationError = validateDisplayName(displayName);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsLoading(true);

    try {
      const updatedUser = await updateUserProfile(trimmedName);
      updateUser(updatedUser);
      setSuccess(true);

      // Auto-clear success message after 3 seconds
      setTimeout(() => {
        setSuccess(false);
      }, 3000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || 'Failed to update display name. Please try again.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const isUnchanged = displayName.trim() === user?.displayName;
  const charCount = displayName.length;

  return (
    <>
      <div className="flex min-h-screen items-center justify-center px-4 py-12">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center">
            <Heading variant="h2" className="mb-2">
              Settings
            </Heading>
            <Text variant="body" color="muted">
              Manage your account preferences
            </Text>
          </div>

          {/* Profile Section */}
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-8">
            <Heading variant="h4" className="mb-4">
              Profile
            </Heading>

            <form onSubmit={handleSubmit} className="space-y-6">
              {success && (
                <div role="alert" className="rounded-md bg-green-50 dark:bg-green-900/20 p-3">
                  <Text variant="bodySmall" className="text-green-800 dark:text-green-200">
                    Display name updated!
                  </Text>
                </div>
              )}

              {error && (
                <div role="alert" className="rounded-md bg-destructive/10 p-3">
                  <Text variant="bodySmall" className="text-destructive">
                    {error}
                  </Text>
                </div>
              )}

              <FormField>
                <FormLabel htmlFor="displayName" required>
                  Display Name
                </FormLabel>
                <Input
                  ref={inputRef}
                  id="displayName"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  disabled={isLoading}
                  maxLength={50}
                  error={!!error}
                  aria-invalid={!!error}
                  aria-describedby={error ? 'displayName-error' : 'displayName-hint'}
                />
                <FormMessage id="displayName-hint" variant="muted">
                  {charCount}/50 characters
                </FormMessage>
              </FormField>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCancel}
                  className="flex-1"
                  disabled={isLoading || isUnchanged}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={isLoading || isUnchanged}
                >
                  {isLoading ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </div>

          {/* Player Identities Section */}
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-8">
            <Heading variant="h4" className="mb-2">
              Player Identities
            </Heading>
            <Text variant="body" color="muted" className="mb-6">
              Claim your player identities from poker games to track your stats
            </Text>

            <PlayerIdentitiesSection />
          </div>

          {/* Security Section */}
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-8">
            <Heading variant="h4" className="mb-4">
              Security
            </Heading>

            <div>
              <Text variant="body" color="muted" className="mb-4">
                Keep your account secure by updating your password regularly.
              </Text>
              <Button onClick={() => setShowChangePassword(true)}>
                Change Password
              </Button>
            </div>
          </div>

          {/* Danger Zone Section */}
          <div className="bg-red-950/20 rounded-lg border border-red-900 p-8">
            <Heading variant="h4" className="mb-2 text-red-500">
              Danger Zone
            </Heading>

            <div className="space-y-4">
              <div>
                <Heading variant="h5" className="mb-2">
                  Delete Account
                </Heading>
                <Text variant="body" color="muted">
                  Once you delete your account, there is no going back. Your account will be
                  permanently deleted, but your games will remain accessible via their public
                  codes. You will lose ownership and cannot manage them anymore.
                </Text>
              </div>

              <Button
                variant="destructive"
                onClick={() => setShowDeleteModal(true)}
              >
                Delete My Account
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Change Password Modal */}
      {showChangePassword && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-border">
              <Heading variant="h4">Change Password</Heading>
              <Button
                onClick={handleCloseChangePassword}
                variant="ghost"
                size="icon-sm"
                disabled={isPasswordLoading}
              >
                <X className="h-6 w-6" />
              </Button>
            </div>

            {/* Body */}
            <form onSubmit={handleChangePasswordSubmit} className="p-6 space-y-6">
              {passwordSuccess && (
                <div role="alert" className="rounded-md bg-green-50 dark:bg-green-900/20 p-3">
                  <Text variant="bodySmall" className="text-green-800 dark:text-green-200">
                    Password updated successfully!
                  </Text>
                </div>
              )}

              {passwordError && (
                <div role="alert" className="rounded-md bg-destructive/10 p-3">
                  <Text variant="bodySmall" className="text-destructive">
                    {passwordError}
                  </Text>
                </div>
              )}

              <FormField>
                <FormLabel htmlFor="currentPassword" required>
                  Current Password
                </FormLabel>
                <div className="relative">
                  <Input
                    id="currentPassword"
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={passwordForm.currentPassword}
                    onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                    disabled={isPasswordLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
                  >
                    {showCurrentPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </FormField>

              <FormField>
                <FormLabel htmlFor="newPassword" required>
                  New Password
                </FormLabel>
                <div className="relative">
                  <Input
                    id="newPassword"
                    type={showNewPassword ? 'text' : 'password'}
                    value={passwordForm.newPassword}
                    onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                    disabled={isPasswordLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
                  >
                    {showNewPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
                {passwordStrength && (
                  <p className={`mt-1 text-sm font-medium ${getStrengthColor(passwordStrength)}`}>
                    Password strength: {getStrengthLabel(passwordStrength)}
                  </p>
                )}
                {!passwordStrength && passwordForm.newPassword.length === 0 && (
                  <FormMessage variant="muted">
                    Password must be at least 12 characters
                  </FormMessage>
                )}
              </FormField>

              <FormField>
                <FormLabel htmlFor="confirmNewPassword" required>
                  Confirm New Password
                </FormLabel>
                <div className="relative">
                  <Input
                    id="confirmNewPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={passwordForm.confirmNewPassword}
                    onChange={(e) => setPasswordForm({ ...passwordForm, confirmNewPassword: e.target.value })}
                    disabled={isPasswordLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
                  >
                    {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </FormField>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCloseChangePassword}
                  className="flex-1"
                  disabled={isPasswordLoading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={isPasswordLoading}
                >
                  {isPasswordLoading ? 'Updating...' : 'Update Password'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Account Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-border">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-6 w-6 text-red-500" />
                <Heading variant="h4">Delete Account</Heading>
              </div>
              <Button
                onClick={handleCloseDeleteModal}
                variant="ghost"
                size="icon-sm"
                disabled={isDeleteLoading}
              >
                <X className="h-6 w-6" />
              </Button>
            </div>

            {/* Body */}
            <form onSubmit={handleDeleteAccountSubmit} className="p-6 space-y-6">
              <div className="space-y-4">
                <div>
                  <Heading variant="h5">Are you absolutely sure?</Heading>
                  <Text variant="body" color="muted" className="mt-2">
                    This action cannot be undone. This will permanently delete your account.
                  </Text>
                </div>

                <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-4">
                  <Text variant="bodySmall" className="text-amber-200">
                    <strong>Note:</strong> Your games will remain accessible via their public
                    codes, but you will lose ownership. They cannot be managed or deleted after
                    your account is deleted.
                  </Text>
                </div>
              </div>

              {deleteError && (
                <div role="alert" className="rounded-md bg-destructive/10 p-3">
                  <Text variant="bodySmall" className="text-destructive">
                    {deleteError}
                  </Text>
                </div>
              )}

              <FormField>
                <FormLabel htmlFor="deletePassword" required>
                  Enter your password to confirm
                </FormLabel>
                <div className="relative">
                  <Input
                    id="deletePassword"
                    type={showDeletePassword ? 'text' : 'password'}
                    value={deleteForm.password}
                    onChange={(e) => setDeleteForm({ ...deleteForm, password: e.target.value })}
                    disabled={isDeleteLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowDeletePassword(!showDeletePassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
                  >
                    {showDeletePassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </FormField>

              <FormField>
                <FormLabel htmlFor="deleteConfirmation" required>
                  Type <code className="bg-gray-800 px-1.5 py-0.5 rounded text-sm">DELETE</code> to confirm
                </FormLabel>
                <Input
                  id="deleteConfirmation"
                  type="text"
                  value={deleteForm.confirmation}
                  onChange={(e) => setDeleteForm({ ...deleteForm, confirmation: e.target.value })}
                  disabled={isDeleteLoading}
                  placeholder="DELETE"
                />
              </FormField>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCloseDeleteModal}
                  className="flex-1"
                  disabled={isDeleteLoading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="destructive"
                  className="flex-1"
                  disabled={isDeleteLoading || !isDeleteButtonEnabled}
                >
                  {isDeleteLoading ? 'Deleting...' : 'Delete Account'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
