/**
 * AI Legal Copilot — Design System
 *
 * Import product UI from here. Prefer these composed exports over deep
 * `@/components/ui/*` imports in feature code (ui/ remains the shadcn layer).
 */

// Tokens & type
export { spacing, motion, typography, type StatusTone } from "./tokens";
export { Text, Heading } from "./typography";
export { FadeIn, Presence } from "./motion";

// Providers
export { DesignSystemProvider } from "./providers/design-system-provider";
export { ThemeProvider } from "./providers/theme-provider";
export { QueryProvider } from "./providers/query-provider";

// Primitives re-exports (single entry)
export { Button, buttonVariants } from "@/components/ui/button";
export { Input } from "@/components/ui/input";
export { Textarea } from "@/components/ui/textarea";
export { Label } from "@/components/ui/label";
export { Checkbox } from "@/components/ui/checkbox";
export { Switch } from "@/components/ui/switch";
export {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
export {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
export {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
export {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
export {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
export { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
export {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
export { Badge } from "@/components/ui/badge";
export { Separator } from "@/components/ui/separator";
export { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
export { Skeleton } from "@/components/ui/skeleton";
export { ScrollArea } from "@/components/ui/scroll-area";
export { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
export {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
export {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
export {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
export {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";
export {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar";
export {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  useFormField,
} from "@/components/ui/form";
export { Toaster } from "@/components/ui/sonner";

// Composed patterns
export { StatusBadge, documentStatusTone } from "./status-badge";
export { EmptyState, EmptyStateAction } from "./empty-state";
export {
  SkeletonText,
  SkeletonCard,
  SkeletonRow,
  SkeletonTable,
} from "./skeleton";
export { PasswordInput } from "./password-input";
export {
  useZodForm,
  FormRoot,
  TextFieldInput,
  TextFieldTextarea,
  TextFieldSelect,
  TextFieldCheckbox,
  TextFieldSwitch,
  FormActions,
} from "./form";
export { UserMenu } from "./user-menu";
export { AppNav, type NavItem } from "./app-nav";
export { AppBreadcrumbs, PageHeader, type Crumb } from "./page-header";
export { toast } from "./toast";
export { Modal, ConfirmDialog, ConfirmButton } from "./modal";
export { DataTable, type Column } from "./data-table";
export { AppSidebar, AppShellFrame, type SidebarLink } from "./app-sidebar";
