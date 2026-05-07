import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff, BookMarked } from "lucide-react";
import { authLogin } from "@/api/generated/endpoints/auth/auth";
import { usersGetMe } from "@/api/generated/endpoints/users/users";
import { useAuthStore, type AuthUser } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setTokens, setUser } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      const tokens = await authLogin(values);
      setTokens(tokens.access_token, tokens.refresh_token);
      const me = await usersGetMe();
      setUser(me as AuthUser);
      const next = searchParams.get("next") ?? "/dashboard";
      navigate(next);
    } catch {
      setServerError("Invalid email or password.");
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
            "The best students don't study harder — they study smarter."
          </blockquote>
          <div className="flex flex-col gap-3">
            {[
              "AI-generated questions from your notes",
              "Collaborative question banks per subject",
              "Practice quizzes with your class",
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
            <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
            <p className="text-sm text-muted-foreground">
              Sign in to your account to continue
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
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
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
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

            {serverError && (
              <p className="text-sm text-destructive">{serverError}</p>
            )}

            <Button type="submit" className="mt-1 w-full" disabled={isSubmitting}>
              {isSubmitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link
              to="/register"
              className="text-foreground underline underline-offset-2 hover:text-primary transition-colors"
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
