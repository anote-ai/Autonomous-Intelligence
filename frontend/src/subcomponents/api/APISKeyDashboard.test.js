import React from "react";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { APISKeyDashboard } from "./APISKeyDashboard";
import { vi } from "vitest";

const mockDispatch = vi.fn();
const mockGetAPIKeys = vi.fn(() => ({ type: "user/getAPIKeys" }));
const mockNavigate = vi.fn();

vi.mock("react-redux", () => ({
  useDispatch: () => mockDispatch,
}));

vi.mock("../../redux/UserSlice", () => ({
  useAPIKeys: () => [],
  useNumCredits: () => 3,
  generateAPIKey: vi.fn(),
  deleteAPIKey: vi.fn(),
  getAPIKeys: (...args) => mockGetAPIKeys(...args),
}));

vi.mock("copy-to-clipboard", () => ({ default: vi.fn() }));

vi.mock("@fortawesome/react-fontawesome", () => ({
  FontAwesomeIcon: () => null,
}));

vi.mock("flowbite-react", () => {
  const sanitizeProps = ({ color, outline, show, size, ...props }) => props;
  const passthrough = ({ children, ...props }) =>
    React.createElement("div", sanitizeProps(props), children);
  const button = ({ children, ...props }) =>
    React.createElement("button", sanitizeProps(props), children);
  const input = (props) => React.createElement("input", props);

  const Table = ({ children, ...props }) =>
    React.createElement("table", props, children);
  Table.Head = passthrough;
  Table.HeadCell = passthrough;
  Table.Body = passthrough;
  Table.Row = passthrough;
  Table.Cell = passthrough;

  const Modal = passthrough;
  Modal.Header = passthrough;
  Modal.Body = passthrough;
  Modal.Footer = passthrough;

  return {
    Button: button,
    Table,
    Badge: passthrough,
    Tooltip: passthrough,
    Modal,
    TextInput: input,
    Label: passthrough,
  };
});

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("APISKeyDashboard", () => {
  beforeEach(() => {
    mockDispatch.mockClear();
    mockGetAPIKeys.mockClear();
    mockNavigate.mockClear();
  });

  it("dispatches getAPIKeys on mount", async () => {
    render(
      <MemoryRouter>
        <APISKeyDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockGetAPIKeys).toHaveBeenCalledTimes(1);
      expect(mockDispatch).toHaveBeenCalledTimes(1);
    });
  });
});
