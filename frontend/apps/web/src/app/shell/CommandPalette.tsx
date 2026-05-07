import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import {
  BookOpen,
  BrainCircuit,
  FileText,
  History,
  LayoutDashboard,
  Settings,
  Upload,
  User,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";

type CommandPaletteProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const NAV_ITEMS = [
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
  { label: "Browse Subjects", icon: BookOpen, to: "/subjects" },
  { label: "Upload Material", icon: Upload, to: "/upload" },
  { label: "My Drafts", icon: FileText, to: "/drafts" },
  { label: "Start a Quiz", icon: BrainCircuit, to: "/quiz" },
  { label: "Quiz History", icon: History, to: "/history" },
  { label: "Profile", icon: User, to: "/profile" },
  { label: "Settings", icon: Settings, to: "/settings" },
];

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();

  function runCommand(fn: () => void) {
    onOpenChange(false);
    fn();
  }

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Navigate to, or search…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          {NAV_ITEMS.map((item) => (
            <CommandItem
              key={item.to}
              value={item.label}
              onSelect={() => runCommand(() => navigate(item.to))}
            >
              <item.icon className="size-4" strokeWidth={1.5} />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Search">
          <CommandItem disabled>
            Search questions — coming in Phase 9
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCommandPalette() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return { open, setOpen };
}
