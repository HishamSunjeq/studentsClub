import { useState } from "react";
import { Link } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { BookMarked, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
});
type FormValues = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit() {
    // Backend endpoint not yet implemented — simulate success
    await new Promise((r) => setTimeout(r, 600));
    setSent(true);
  }

  return (
    <div className="flex min-h-screen">
      {/* Brand panel */}
      <div className="hidden lg:flex lg:w-5/12 flex-col justify-between border-r border-border bg-surface-low p-12">
        <div className="flex items-center gap-3">
          <BookMarked className="size-5 text-primary" strokeWidth={1.5} />
          <span className="text-lg font-bold tracking-tight">StudentsClub</span>
        </div>
        <div className="flex flex-col gap-4">
          <p className="text-xl font-light leading-relaxed text-muted-foreground">
            We'll send a reset link to your email address. Check your inbox and
            follow the instructions.
          </p>
        </div>
        <p className="text-xs text-muted-foreground">© 2026 StudentsClub</p>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 flex-col items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          {sent ? (
            <div className="flex flex-col items-center gap-4 text-center">
              <CheckCircle className="size-12 text-primary" strokeWidth={1.5} />
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Check your inbox</h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  If an account exists for that email, we've sent a password reset
                  link. It may take a minute to arrive.
                </p>
              </div>
              <Link to="/login">
                <Button variant="outline" className="mt-2">
                  Back to sign in
                </Button>
              </Link>
            </div>
          ) : (
            <>
              <div className="mb-8 flex flex-col gap-1">
                <h1 className="text-2xl font-semibold tracking-tight">Forgot password?</h1>
                <p className="text-sm text-muted-foreground">
                  Enter your email and we'll send you a reset link.
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

                <Button type="submit" className="mt-1 w-full" disabled={isSubmitting}>
                  {isSubmitting ? "Sending…" : "Send reset link"}
                </Button>
              </form>

              <p className="mt-6 text-center text-sm text-muted-foreground">
                Remembered it?{" "}
                <Link
                  to="/login"
                  className="text-foreground underline underline-offset-2 hover:text-primary transition-colors"
                >
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
