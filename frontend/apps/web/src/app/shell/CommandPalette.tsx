import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  BrainCircuit,
  FileText,
  GraduationCap,
  History,
  LayoutDashboard,
  Search as SearchIcon,
  Settings,
  Sparkles,
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
import { searchQuery } from "@/api/generated/endpoints/search/search";

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
  const [query, setQuery] = useState("");

  // Debounce + only fire when palette is open and query is non-trivial
  const [debouncedQuery, setDebouncedQuery] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query.trim()), 200);
    return () => clearTimeout(t);
  }, [query]);

  const { data: searchData } = useQuery({
    queryKey: ["search", debouncedQuery],
    queryFn: () => searchQuery({ q: debouncedQuery, limit: 8 }),
    enabled: open && debouncedQuery.length >= 2,
    staleTime: 30_000,
  });

  // Reset query when palette closes
  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  function runCommand(fn: () => void) {
    onOpenChange(false);
    fn();
  }

  const hasSearchResults =
    !!searchData &&
    (searchData.subjects.length > 0 || searchData.question_sets.length > 0);

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput
        value={query}
        onValueChange={setQuery}
        placeholder="Navigate to, or search subjects and question sets…"
      />
      <CommandList>
        <CommandEmpty>
          {debouncedQuery.length >= 2
            ? "No results found."
            : "Type at least 2 characters to search."}
        </CommandEmpty>

        {/* Search results */}
        {hasSearchResults && (
          <>
            {searchData.subjects.length > 0 && (
              <CommandGroup heading="Subjects">
                {searchData.subjects.map((s) => (
                  <CommandItem
                    key={`subject-${s.id}`}
                    value={`subject-${s.code}-${s.name}`}
                    onSelect={() =>
                      runCommand(() => navigate(`/subjects/${s.id}`))
                    }
                  >
                    <GraduationCap className="size-4" strokeWidth={1.5} />
                    <span className="flex-1">{s.name}</span>
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {s.code}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {searchData.question_sets.length > 0 && (
              <CommandGroup heading="Question sets">
                {searchData.question_sets.map((qs) => (
                  <CommandItem
                    key={`qs-${qs.question_set_id}`}
                    value={`qs-${qs.title}-${qs.subject_code}`}
                    onSelect={() =>
                      runCommand(() => navigate(`/subjects/${qs.subject_id}`))
                    }
                  >
                    <Sparkles className="size-4" strokeWidth={1.5} />
                    <span className="flex-1 truncate">{qs.title}</span>
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {qs.subject_code}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            <CommandSeparator />
          </>
        )}

        {/* Navigation always available */}
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

        {debouncedQuery.length < 2 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Search">
              <CommandItem disabled>
                <SearchIcon className="size-4" strokeWidth={1.5} />
                Type to search subjects and question sets
              </CommandItem>
            </CommandGroup>
          </>
        )}
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
