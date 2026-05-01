import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiInstance } from "@/api/client";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();

  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    college: "",
    academic_year: "1",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data: tokens } = await apiInstance.post<{
        access_token: string;
        refresh_token: string;
      }>("/api/v1/auth/register", {
        ...form,
        academic_year: Number(form.academic_year),
      });

      setTokens(tokens.access_token, tokens.refresh_token);

      const { data: me } = await apiInstance.get("/api/v1/users/me");
      setUser(me);

      navigate("/");
    } catch (err: unknown) {
      if (
        err &&
        typeof err === "object" &&
        "response" in err &&
        (err as { response?: { status?: number } }).response?.status === 409
      ) {
        setError("An account with that email already exists");
      } else {
        setError("Registration failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Create account</CardTitle>
          <CardDescription>Join StudentsClub to start practising</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="full_name">Full name</Label>
              <Input
                id="full_name"
                value={form.full_name}
                onChange={(e) => update("full_name", e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="college">College / Faculty</Label>
              <Input
                id="college"
                value={form.college}
                onChange={(e) => update("college", e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="academic_year">Academic year</Label>
              <Input
                id="academic_year"
                type="number"
                min={1}
                max={7}
                value={form.academic_year}
                onChange={(e) => update("academic_year", e.target.value)}
                required
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Creating account…" : "Create account"}
            </Button>
            <p className="text-sm text-center text-muted-foreground">
              Already have an account?{" "}
              <Link to="/login" className="underline underline-offset-2 hover:text-foreground">
                Sign in
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
