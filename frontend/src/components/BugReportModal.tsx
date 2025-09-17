import { X, Bug, Send, AlertCircle } from 'lucide-react';
import React, { useState } from 'react';
import type { BugReportData } from '../api/bugReport';
import { Button } from '../shared/ui/button';
import { FormField, FormLabel, FormMessage } from '../shared/ui/form-field';
import { Input } from '../shared/ui/input';
import { Select } from '../shared/ui/select';
import { Textarea } from '../shared/ui/textarea';
import { Heading, Text } from '../shared/ui/typography';

interface BugReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: BugReportData) => Promise<void>;
}

const BugReportModal: React.FC<BugReportModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [formData, setFormData] = useState<BugReportData>({
    description: '',
    steps_to_reproduce: '',
    category: 'Other',
    user_email: '',
    url: window.location.href,
    user_agent: navigator.userAgent,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const categories = [
    'UI Issue',
    'Functionality',
    'Performance',
    'Data Accuracy',
    'Other'
  ];

  // Extract game code from URL if present
  React.useEffect(() => {
    const path = window.location.pathname;
    const gameCodeMatch = path.match(/\/summary\/([A-Z0-9]{5})/);
    if (gameCodeMatch && gameCodeMatch[1]) {
      setFormData(prev => {
        const newData = { ...prev };
        newData.game_code = gameCodeMatch[1];
        return newData;
      });
    }
  }, []);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    } else if (formData.description.length < 10) {
      newErrors.description = 'Description must be at least 10 characters';
    } else if (formData.description.length > 5000) {
      newErrors.description = 'Description must be less than 5000 characters';
    }

    if (formData.steps_to_reproduce.length > 3000) {
      newErrors.steps_to_reproduce = 'Steps must be less than 3000 characters';
    }

    if (formData.user_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.user_email)) {
      newErrors.user_email = 'Please enter a valid email address';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(formData);

      // Reset form on success
      const resetData: BugReportData = {
        description: '',
        steps_to_reproduce: '',
        category: 'Other',
        user_email: '',
        url: window.location.href,
        user_agent: navigator.userAgent,
      };

      if (formData.game_code) {
        resetData.game_code = formData.game_code;
      }

      setFormData(resetData);

      onClose();
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to submit bug report:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (field: keyof BugReportData) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setFormData(prev => ({ ...prev, [field]: e.target.value }));

    // Clear error when user starts typing
    if (errors[field as string]) {
      setErrors(prev => ({ ...prev, [field as string]: '' }));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <Bug className="h-6 w-6 text-primary" />
            <Heading variant="h4">Report a Bug</Heading>
          </div>
          <Button
            onClick={onClose}
            variant="ghost"
            size="icon-sm"
            disabled={isSubmitting}
          >
            <X className="h-6 w-6" />
          </Button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="space-y-6">
            {/* Description */}
            <FormField>
              <FormLabel htmlFor="description" required>
                Bug Description
              </FormLabel>
              <Textarea
                id="description"
                value={formData.description}
                onChange={handleChange('description')}
                placeholder="Please describe the bug you encountered..."
                className="h-32"
                error={!!errors.description}
                disabled={isSubmitting}
              />
              {errors.description && (
                <FormMessage variant="error" className="flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {errors.description}
                </FormMessage>
              )}
              <FormMessage variant="muted">
                {formData.description.length}/5000 characters
              </FormMessage>
            </FormField>

            {/* Steps to Reproduce */}
            <FormField>
              <FormLabel htmlFor="steps">
                Steps to Reproduce (optional)
              </FormLabel>
              <Textarea
                id="steps"
                value={formData.steps_to_reproduce}
                onChange={handleChange('steps_to_reproduce')}
                placeholder="1. Go to...&#10;2. Click on...&#10;3. See error..."
                className="h-24"
                error={!!errors.steps_to_reproduce}
                disabled={isSubmitting}
              />
              {errors.steps_to_reproduce && (
                <FormMessage variant="error" className="flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {errors.steps_to_reproduce}
                </FormMessage>
              )}
              <FormMessage variant="muted">
                {formData.steps_to_reproduce.length}/3000 characters
              </FormMessage>
            </FormField>

            {/* Category */}
            <FormField>
              <FormLabel htmlFor="category">
                Category
              </FormLabel>
              <Select
                id="category"
                value={formData.category}
                onChange={handleChange('category')}
                disabled={isSubmitting}
              >
                {categories.map(category => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </Select>
            </FormField>

            {/* Email */}
            <FormField>
              <FormLabel htmlFor="email">
                Your Email (optional)
              </FormLabel>
              <Input
                type="email"
                id="email"
                value={formData.user_email}
                onChange={handleChange('user_email')}
                placeholder="your.email@example.com"
                error={!!errors.user_email}
                disabled={isSubmitting}
              />
              {errors.user_email && (
                <FormMessage variant="error" className="flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {errors.user_email}
                </FormMessage>
              )}
              <FormMessage variant="muted">
                Optional: If you'd like us to follow up with you about this bug
              </FormMessage>
            </FormField>

            {/* Context Info (Read-only) */}
            <div className="bg-muted/50 p-4 rounded-md">
              <Text variant="bodySmall" weight="medium" className="mb-2">Automatically Included Info</Text>
              <div className="space-y-1">
                <Text variant="caption" color="muted"><strong>Page:</strong> {formData.url}</Text>
                {formData.game_code && <Text variant="caption" color="muted"><strong>Game Code:</strong> {formData.game_code}</Text>}
                <Text variant="caption" color="muted"><strong>Browser:</strong> {navigator.userAgent.includes('Chrome') ? 'Chrome' :
                  navigator.userAgent.includes('Firefox') ? 'Firefox' :
                  navigator.userAgent.includes('Safari') ? 'Safari' : 'Other'}</Text>
              </div>
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-border">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={isSubmitting}
          >
            <Text variant="bodySmall" weight="medium">Cancel</Text>
          </Button>
          <Button
            type="submit"
            onClick={handleSubmit}
            disabled={isSubmitting || !formData.description.trim()}
            className="flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                <Text variant="bodySmall" weight="medium">Submitting...</Text>
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                <Text variant="bodySmall" weight="medium">Submit Bug Report</Text>
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default BugReportModal;