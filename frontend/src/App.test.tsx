import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";

afterEach(() => vi.restoreAllMocks());

test("renders heading and personas from the API", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify([{ id: "student", name: "Student", description: "x" }]),
      { headers: { "Content-Type": "application/json" } },
    ),
  );
  render(<App />);
  expect(screen.getByText("Talk to Alan Turing")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Student")).toBeInTheDocument());
});
