"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface User {
    email: string;
    full_name?: string;
}

interface UserAvatarProps {
  user?: User | null;
}

const getInitials = (name?: string, email?: string): string => {
  if (name) {
    const parts = name.split(" ");
    if (parts.length > 1 && parts[0] && parts[parts.length - 1]) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }
  if (email) {
    return email.charAt(0).toUpperCase();
  }
  return "A";
};

export const UserAvatar = ({ user }: UserAvatarProps) => {
  return (
    <Avatar className="h-9 w-9">
      {/* The backend doesn't provide image URLs yet, so this will always use the fallback */}
      <AvatarImage src="" alt={user?.full_name || user?.email} />
      <AvatarFallback>{getInitials(user?.full_name, user?.email)}</AvatarFallback>
    </Avatar>
  );
};