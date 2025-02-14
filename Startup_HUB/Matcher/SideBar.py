import reflex as rx

def navbar() -> rx.Component:
    return rx.hstack(
        rx.avatar(
            src="profile.jpg",
            size="sm",
            class_name="cursor-pointer"
        ),
        rx.spacer(),
        rx.hstack(
            rx.icon("search", class_name="text-gray-600"),
            rx.icon("shield", class_name="text-gray-600"),
            rx.icon("settings", class_name="text-gray-600"),
            spacing="4"
        ),
        width="full",
        padding="4",
        bg="lightblue"
    )

def navigation() -> rx.Component:
    return rx.hstack(
        rx.text("Matches", class_name="font-medium"),
        rx.text("liked", class_name="font-medium"),
        rx.text("Messages", class_name="font-medium"),
        spacing="6",
        padding="4"
    )

def profile_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.image(
                src="character.jpg",
                class_name="w-full h-96 object-cover rounded-t-3xl"
            ),
            rx.box(
                rx.hstack(
                    rx.dot(color="green"),
                    rx.text("Recently Active", class_name="text-sm text-gray-400")
                ),
                rx.heading("Soukaku", size="lg"),
                rx.text("Profession: Finance Consultant", class_name="text-gray-400"),
                padding="4",
                spacing="2",
                bg="navy",
                color="white",
                width="full",
                border_radius="xl"
            ),
            spacing="0",
            width="full"
        ),
        class_name="w-96 overflow-hidden shadow-xl"
    )

def action_buttons() -> rx.Component:
    return rx.hstack(
        rx.circle_button(
            rx.icon("arrow_back", color="yellow"),
            bg="transparent",
        ),
        rx.circle_button(
            rx.icon("close", color="red"),
            bg="transparent",
        ),
        rx.circle_button(
            rx.icon("star", color="lightblue"),
            bg="transparent",
        ),
        rx.circle_button(
            rx.icon("check", color="green"),
            bg="transparent",
        ),
        rx.circle_button(
            rx.icon("visibility", color="orange"),
            bg="transparent",
        ),
        spacing="2",
        justify="center",
        padding_y="4"
    )

def index() -> rx.Component:
    return rx.box(
        navbar(),
        navigation(),
        rx.center(
            rx.vstack(
                profile_card(),
                action_buttons(),
                spacing="0"
            ),
            padding_top="8"
        ),
        bg="#1a1a1a",
        min_height="100vh"
    )

app = rx.App()
app.add_page(index)