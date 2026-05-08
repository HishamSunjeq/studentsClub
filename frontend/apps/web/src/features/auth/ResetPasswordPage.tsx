import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { BookMarked, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthResetPassword } from "@/api/generated/endpoints/auth/auth";

const schema = z
  .object({
    new_password: z.string().min(8, "Password must be at least 8 characters").max(128),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();
  const [done, setDone] = useState(false);
  const resetPasswordMutation = useAuthResetPassword();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    try {
      await resetPasswordMutation.mutateAsync({
        data: {
          token,
          new_password: values.new_password,
        },
      });
      setDone(true);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "This reset link is invalid or has expired");
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="text-center">
          <p className="text-muted-foreground">Invalid or missing reset token.</p>
          <Link to="/forgot-password">
            <Button variant="outline" className="mt-4">
              Request a new link
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      {/* Brand panel */}
      <div className="hidden lg:flex lg:w-5/12 flex-col justify-between border-r border-border bg-surface-low p-12">
        <div className="flex items-center gap-3">
          <BookMarked className="size-5 text-primary" strokeWidth={1.5} />
          <span className="text-lg font-bold tracking-tight">StudentsClub</span>
        </div>
        <p className="text-xl font-light leading-relaxed text-muted-foreground">
          Choose a strong password you haven't used before.
        </p>
        <p className="text-xs text-muted-foreground">© 2026 StudentsClub</p>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 flex-col items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          {done ? (
            <div className="flex flex-col items-center gap-4 text-center">
              <CheckCircle className="size-12 text-primary" strokeWidth={1.5} />
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Password reset!</h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Your password has been updated. You can now sign in with your new password.
                </p>
              </div>
              <Button className="mt-2" onClick={() => navigate("/login")}>
                Sign in
              </Button>
            </div>
          ) : (
            <>
              <div className="mb-8 flex flex-col gap-1">
                <h1 className="text-2xl font-semibold tracking-tight">Set new password</h1>
                <p className="text-sm text-muted-foreground">
                  Enter your new password below.
                </p>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="new_password">New password</Label>
                  <Input
                    id="new_password"
                    type="password"
                    autoComplete="new-password"
                    {...register("new_password")}
                  />
                  {errors.new_password && (
                    <p className="text-xs text-destructive">{errors.new_password.message}</p>
                  )}
                </div>

                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="confirm_password">Confirm password</Label>
                  <Input
                    id="confirm_password"
                    type="password"
                    autoComplete="new-password"
                    {...register("confirm_password")}
                  />
                  {errors.confirm_password && (
                    <p className="text-xs text-destructive">{errors.confirm_password.message}</p>
                  )}
                </div>

                <Button
                  type="submit"
                  className="mt-1 w-full"
                  disabled={isSubmitting || resetPasswordMutation.isPending}
                >
                  {isSubmitting || resetPasswordMutation.isPending
                    ? "Saving…"
                    : "Reset password"}
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
