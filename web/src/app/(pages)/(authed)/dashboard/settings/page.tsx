"use client";

import React, { useState } from 'react';
import { useAuth } from '@/components/global/providers';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Sun, Moon, Laptop } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();
  const { setTheme } = useTheme();

  // State for forms
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  // State for support dialog
  const [supportSubject, setSupportSubject] = useState('');
  const [supportMessage, setSupportMessage] = useState('');
  const [isSupportDialogOpen, setIsSupportDialogOpen] = useState(false);

  const handleProfileSave = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success('Profile updated successfully.');
  };

  const handlePasswordChange = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match.');
      return;
    }
    if (newPassword.length < 8) {
      toast.error('New password must be at least 8 characters long.');
      return;
    }
    
    // Simulate API call
    const promise = new Promise((resolve) => setTimeout(resolve, 1500));
    toast.promise(promise, {
      loading: 'Updating password...',
      success: () => {
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        return 'Password updated successfully.';
      },
      error: 'Failed to update password.',
    });
  };

  const handleSupportSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!supportSubject.trim() || !supportMessage.trim()) {
      toast.error("Please fill out both subject and message fields.");
      return;
    }

    // Simulate sending the message
    const promise = () => new Promise((resolve) => setTimeout(resolve, 2000));
    toast.promise(promise, {
      loading: 'Sending your message to our support team...',
      success: () => {
        setIsSupportDialogOpen(false);
        setSupportSubject('');
        setSupportMessage('');
        return "Your message has been sent. We'll get back to you shortly.";
      },
      error: 'Failed to send message. Please try again.',
    });
  };

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Settings</h1>
      </div>
      
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>My Profile</CardTitle>
            <CardDescription>Update your personal information.</CardDescription>
          </CardHeader>
          <form onSubmit={handleProfileSave}>
            <CardContent className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="fullName">Full Name</Label>
                <Input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={user?.email || ''} disabled />
              </div>
            </CardContent>
            <CardFooter className="border-t px-6 py-4">
              <Button type="submit">Save Changes</Button>
            </CardFooter>
          </form>
        </Card>

        {/* Security Card */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Security</CardTitle>
            <CardDescription>Manage your password and account security.</CardDescription>
          </CardHeader>
          <form onSubmit={handlePasswordChange}>
            <CardContent className="space-y-4">
               <div className="space-y-1">
                <Label htmlFor="currentPassword">Current Password</Label>
                <Input id="currentPassword" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label htmlFor="newPassword">New Password</Label>
                  <Input id="newPassword" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <Input id="confirmPassword" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
                </div>
              </div>
            </CardContent>
            <CardFooter className="border-t px-6 py-4">
              <Button type="submit">Update Password</Button>
            </CardFooter>
          </form>
        </Card>

        {/* Interface Card */}
        <Card>
            <CardHeader>
                <CardTitle>Interface</CardTitle>
                <CardDescription>Customize the look and feel of the application.</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-3 gap-2">
                <Button variant="outline" onClick={() => setTheme('light')}><Sun className="mr-2 h-4 w-4" />Light</Button>
                <Button variant="outline" onClick={() => setTheme('dark')}><Moon className="mr-2 h-4 w-4" />Dark</Button>
                <Button variant="outline" onClick={() => setTheme('system')}><Laptop className="mr-2 h-4 w-4" />System</Button>
            </CardContent>
        </Card>

        {/* Support Card */}
        <Card className="lg:col-span-2">
            <CardHeader>
                <CardTitle>Support</CardTitle>
                <CardDescription>Need help? Contact our support team directly.</CardDescription>
            </CardHeader>
            <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                    If you encounter any issues or have questions about your analysis, please don't hesitate to reach out. Our team of specialists is available to assist you.
                </p>
                <Dialog open={isSupportDialogOpen} onOpenChange={setIsSupportDialogOpen}>
                    <DialogTrigger asChild>
                        <Button>Contact Support</Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[425px]">
                        <form onSubmit={handleSupportSubmit}>
                            <DialogHeader>
                                <DialogTitle>Contact Support</DialogTitle>
                                <DialogDescription>
                                    Describe your issue below. A support ticket will be created and we'll respond via email.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="space-y-2">
                                    <Label htmlFor="subject" className="text-right">Subject</Label>
                                    <Input id="subject" value={supportSubject} onChange={(e) => setSupportSubject(e.target.value)} placeholder="e.g., Issue with Report #12345" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="message" className="text-right">Message</Label>
                                    <Textarea id="message" value={supportMessage} onChange={(e) => setSupportMessage(e.target.value)} placeholder="Please provide as much detail as possible..." className="min-h-[120px]" />
                                </div>
                            </div>
                            <DialogFooter>
                                <DialogClose asChild><Button type="button" variant="ghost">Cancel</Button></DialogClose>
                                <Button type="submit">Send Message</Button>
                            </DialogFooter>
                        </form>
                    </DialogContent>
                </Dialog>
            </CardContent>
        </Card>
      </div>
    </div>
  );
}