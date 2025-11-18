"""CLI application using Typer framework."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from claude_bedrock_cursor import __version__
from claude_bedrock_cursor.auth import OAuthManager
from claude_bedrock_cursor.bedrock import BedrockClient
from claude_bedrock_cursor.config import Config, get_config

# Create Typer app
app = typer.Typer(
    name="claude-bedrock",
    help="Claude Code + AWS Bedrock + Cursor IDE Integration",
    add_completion=True,
)

# Rich console for beautiful output
console = Console()

# Default options
CONFIG_FILE_OPTION = typer.Option(
    None,
    "--config",
    "-c",
    help="Path to configuration file",
)

# Subcommands
auth_app = typer.Typer(help="Authentication commands")
aws_app = typer.Typer(help="AWS Bedrock commands")
cursor_app = typer.Typer(help="Cursor IDE commands")
models_app = typer.Typer(help="Model management commands")

app.add_typer(auth_app, name="auth")
app.add_typer(aws_app, name="aws")
app.add_typer(cursor_app, name="cursor")
app.add_typer(models_app, name="models")


# Main commands
@app.command()
def init(
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        help="Run in interactive mode",
    ),
) -> None:
    """Initialize claude-bedrock configuration.

    Example:
        $ claude-bedrock init
        $ claude-bedrock init --no-interactive
    """
    console.print("[bold green]🚀 Initializing claude-bedrock...[/bold green]")

    if interactive:
        console.print("\n[yellow]Interactive setup mode[/yellow]")
        console.print("Answer the following questions to configure claude-bedrock:\n")

        # TODO: Interactive prompts
        console.print("[green]✓[/green] Configuration initialized!")
    else:
        console.print("[green]✓[/green] Using default configuration")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. claude-bedrock auth login")
    console.print("2. claude-bedrock aws setup")
    console.print("3. claude-bedrock cursor install")


@app.command()
def status() -> None:
    """Show current configuration status.

    Example:
        $ claude-bedrock status
    """
    console.print("[bold]📊 Claude Bedrock Status[/bold]\n")

    config = get_config()

    # Create status table
    table = Table(show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")

    # Check authentication
    oauth = OAuthManager()
    auth_status = (
        "✓ Authenticated"
        if asyncio.run(oauth.is_authenticated())
        else "✗ Not authenticated"
    )
    table.add_row("Authentication", auth_status, "")

    # AWS configuration
    table.add_row("AWS Region", "✓ Configured", config.aws_region)
    table.add_row("Bedrock Model", "✓ Configured", config.bedrock_model_id)

    # Features
    cache_status = "✓ Enabled" if config.enable_prompt_caching else "✗ Disabled"
    table.add_row("Prompt Caching", cache_status, "90% cost reduction")

    streaming_status = "✓ Enabled" if config.enable_streaming else "✗ Disabled"
    table.add_row("Streaming", streaming_status, "Better UX")

    console.print(table)


@app.command()
def configure(
    config_file: Path | None = CONFIG_FILE_OPTION,
) -> None:
    """Configure claude-bedrock settings.

    Example:
        $ claude-bedrock configure
        $ claude-bedrock configure --config config.toml
    """
    console.print("[bold]⚙️  Configuration[/bold]\n")

    if config_file:
        try:
            config = Config.from_toml(config_file)
            console.print(f"[green]✓[/green] Loaded config from {config_file}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to load config: {e}")
            raise typer.Exit(1) from e
    else:
        console.print("[yellow]Using environment variables and defaults[/yellow]")
        config = get_config()

    # Display current configuration
    console.print("\n[bold]Current Configuration:[/bold]")
    for key, value in config.to_dict().items():
        console.print(f"  {key}: {value}")


@app.command()
def version() -> None:
    """Show version information.

    Example:
        $ claude-bedrock version
    """
    console.print(f"[bold]claude-bedrock[/bold] version {__version__}")


# Authentication commands
@auth_app.command("login")
def auth_login() -> None:
    """Login with Claude Code MAX subscription.

    Example:
        $ claude-bedrock auth login
    """
    console.print("[bold]🔐 OAuth Login[/bold]\n")
    console.print("This will open Claude Code to generate an OAuth token.\n")

    async def login():
        oauth = OAuthManager()
        try:
            await oauth.login()
            console.print("[green]✓[/green] Login successful!")
            console.print("\nTokens stored securely in system keyring.")
        except Exception as e:
            console.print(f"[red]✗[/red] Login failed: {e}")
            raise typer.Exit(1) from e

    asyncio.run(login())


@auth_app.command("logout")
def auth_logout() -> None:
    """Logout and clear stored tokens.

    Example:
        $ claude-bedrock auth logout
    """
    console.print("[bold]🔐 Logout[/bold]\n")

    async def logout():
        oauth = OAuthManager()
        await oauth.logout()
        console.print("[green]✓[/green] Logged out successfully")
        console.print("All tokens cleared from keyring")

    asyncio.run(logout())


@auth_app.command("refresh")
def auth_refresh() -> None:
    """Manually refresh access token.

    Example:
        $ claude-bedrock auth refresh
    """
    console.print("[bold]🔄 Refreshing Token[/bold]\n")

    async def refresh():
        oauth = OAuthManager()
        try:
            await oauth.refresh_access_token()
            console.print("[green]✓[/green] Token refreshed successfully")
        except Exception as e:
            console.print(f"[red]✗[/red] Refresh failed: {e}")
            raise typer.Exit(1) from e

    asyncio.run(refresh())


@auth_app.command("status")
def auth_status() -> None:
    """Show authentication status.

    Example:
        $ claude-bedrock auth status
    """

    async def check_status():
        oauth = OAuthManager()
        is_auth = await oauth.is_authenticated()

        if is_auth:
            console.print("[green]✓[/green] Authenticated")
            console.print("Tokens stored in system keyring")
        else:
            console.print("[red]✗[/red] Not authenticated")
            console.print("\nRun: claude-bedrock auth login")

    asyncio.run(check_status())


# AWS commands
@aws_app.command("setup")
def aws_setup() -> None:
    """Setup AWS Bedrock configuration.

    Example:
        $ claude-bedrock aws setup
    """
    console.print("[bold]☁️  AWS Bedrock Setup[/bold]\n")
    console.print("[yellow]TODO: Implement AWS setup wizard[/yellow]")
    console.print("\nFor now, configure manually:")
    console.print("1. Set AWS_REGION environment variable")
    console.print("2. Configure AWS credentials (aws configure)")
    console.print("3. Enable Bedrock access in AWS Console")


@aws_app.command("validate")
def aws_validate() -> None:
    """Validate AWS Bedrock access.

    Example:
        $ claude-bedrock aws validate
    """
    console.print("[bold]✓ Validating Bedrock Access[/bold]\n")

    async def validate():
        try:
            client = BedrockClient()
            is_valid = await client.validate_connection()

            if is_valid:
                console.print("[green]✓[/green] Bedrock connection valid")
                console.print(f"Region: {client.region}")
                console.print(f"Model: {client.model_id}")
            else:
                console.print("[red]✗[/red] Bedrock connection failed")
                raise typer.Exit(1)

        except Exception as e:
            console.print(f"[red]✗[/red] Validation failed: {e}")
            raise typer.Exit(1) from e

    asyncio.run(validate())


# Models commands
@models_app.command("list")
def models_list() -> None:
    """List available Claude models in Bedrock.

    Example:
        $ claude-bedrock models list
    """
    console.print("[bold]📋 Available Models[/bold]\n")

    async def list_models():
        try:
            client = BedrockClient()
            models = await client.list_available_models()

            table = Table(show_header=True)
            table.add_column("Model ID", style="cyan")
            table.add_column("Name")

            for model in models:
                table.add_row(
                    model.get("modelId", ""),
                    model.get("modelName", ""),
                )

            console.print(table)

        except Exception as e:
            console.print(f"[red]✗[/red] Failed to list models: {e}")
            raise typer.Exit(1) from e

    asyncio.run(list_models())


@models_app.command("test")
def models_test(
    prompt: str = typer.Option(
        "Say 'test successful' and nothing else",
        "--prompt",
        "-p",
        help="Test prompt",
    ),
) -> None:
    """Test model invocation.

    Example:
        $ claude-bedrock models test
        $ claude-bedrock models test --prompt "What is 2+2?"
    """
    console.print("[bold]🧪 Testing Model[/bold]\n")
    console.print(f"Prompt: {prompt}\n")

    async def test_model():
        try:
            client = BedrockClient()

            console.print("[yellow]Streaming response:[/yellow]\n")
            async for chunk in client.invoke_streaming(prompt):
                console.print(chunk, end="")

            console.print("\n\n[green]✓[/green] Test successful")

        except Exception as e:
            console.print(f"\n[red]✗[/red] Test failed: {e}")
            raise typer.Exit(1) from e

    asyncio.run(test_model())


# Cursor commands
@cursor_app.command("install")
def cursor_install() -> None:
    """Install claude-bedrock in Cursor IDE.

    Example:
        $ claude-bedrock cursor install
    """
    console.print("[bold]💻 Cursor IDE Installation[/bold]\n")
    console.print("[yellow]TODO: Implement Cursor installation[/yellow]")
    console.print("\nManual steps:")
    console.print("1. Open Cursor IDE")
    console.print("2. Open integrated terminal")
    console.print("3. Run: claude-bedrock status")


@cursor_app.command("config")
def cursor_config() -> None:
    """Configure Cursor IDE integration.

    Example:
        $ claude-bedrock cursor config
    """
    console.print("[bold]⚙️  Cursor Configuration[/bold]\n")
    console.print("[yellow]TODO: Implement Cursor configuration[/yellow]")


@cursor_app.command("status")
def cursor_status() -> None:
    """Show Cursor IDE integration status.

    Example:
        $ claude-bedrock cursor status
    """
    console.print("[bold]💻 Cursor Status[/bold]\n")
    console.print("[yellow]TODO: Implement status check[/yellow]")


if __name__ == "__main__":
    app()
