import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, BookMarked } from "lucide-react";
import { authRegister } from "@/api/generated/endpoints/auth/auth";
import { usersGetMe } from "@/api/generated/endpoints/users/users";
import { useAuthStore, type AuthUser } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  full_name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  college: z.string().min(2, "College / faculty is required"),
  academic_year: z.coerce.number().int().min(1, "Min year is 1").max(7, "Max year is 7"),
});
type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { academic_year: 1 },
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      const tokens = await authRegister(values);
      setTokens(tokens.access_token, tokens.refresh_token);
      const me = await usersGetMe();
      setUser(me as AuthUser);
      navigate("/dashboard");
    } catch (err: unknown) {
      const status =
        err &&
        typeof err === "object" &&
        "response" in err &&
        (err as { response?: { status?: number } }).response?.status;
      setServerError(
        status === 409
          ? "An account with that email already exists."
          : "Registration failed. Please try again.",
      );
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Brand panel */}
      <div className="hidden lg:flex lg:w-5/12 flex-col justify-between border-r border-border bg-surface-low p-12">
        <div className="flex items-center gap-3">
          <BookMarked className="size-5 text-primary" strokeWidth={1.5} />
          <span className="text-lg font-bold tracking-tight">StudentsClub</span>
        </div>
        <div className="flex flex-col gap-6">
          <blockquote className="font-serif text-2xl font-light italic leading-relaxed text-foreground">
            "Upload your notes, practice with your class, ace your exams."
          </blockquote>
          <div className="flex flex-col gap-3">
            {[
              "AI-generated questions in seconds",
              "Review and publish to your class",
              "Track your progress over time",
            ].map((feat) => (
              <div key={feat} className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="size-1.5 flex-shrink-0 rounded-full bg-primary" />
                {feat}
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-muted-foreground">© 2026 StudentsClub</p>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 flex-col items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex flex-col gap-1">
            <h1 className="text-2xl font-semibold tracking-tight">Create your account</h1>
            <p className="text-sm text-muted-foreground">
              Join StudentsClub to start practising
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="full_name">Full name</Label>
              <Input
                id="full_name"
                placeholder="Jane Smith"
                {...register("full_name")}
              />
              {errors.full_name && (
                <p className="text-xs text-destructive">{errors.full_name.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@university.edu"
                {...register("email")}
              />
              {errors.email && (
                <p className="text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="Min. 8 characters"
                  className="pr-10"
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="size-4" strokeWidth={1.5} />
                  ) : (
                    <Eye className="size-4" strokeWidth={1.5} />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="college">College / Faculty</Label>
              <Input
                id="college"
                placeholder="e.g. Engineering"
                {...register("college")}
              />
              {errors.college && (
                <p className="text-xs text-destructive">{errors.college.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="academic_year">Academic year</Label>
              <Input
                id="academic_year"
                type="number"
                min={1}
                max={7}
                {...register("academic_year")}
              />
              {errors.academic_year && (
                <p className="text-xs text-destructive">{errors.academic_year.message}</p>
              )}
            </div>

            {serverError && (
              <p className="text-sm text-destructive">{serverError}</p>
            )}

            <Button type="submit" className="mt-1 w-full" disabled={isSubmitting}>
              {isSubmitting ? "Creating account…" : "Create account"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-foreground underline underline-offset-2 hover:text-primary transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
