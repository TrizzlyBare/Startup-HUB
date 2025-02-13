import reflex as rx

def navbar() -> rx.Component:
    return rx.hstack(
        rx.avatar(
            src="profile.jpg",
            size="2",
            class_name="cursor-pointer"
        ),
        rx.spacer(),
        rx.hstack(
            rx.icon("search"),
            rx.icon("shield"),
            rx.icon("settings"),
            spacing="4",
            color="gray"
        ),
        width="full",
        padding="4",
        bg="lightblue"
    )

def navigation() -> rx.Component:
    return rx.hstack(
        rx.text("Matches", font_weight="bold"),
        rx.text("liked", font_weight="bold"),
        rx.text("Messages", font_weight="bold"),
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
                    rx.icon("circle"),
                    rx.text("Recently Active", color="gray", size="8")
                ),
                rx.heading("Soukaku", size="1"),
                rx.text("Profession: Finance Consultant", color="gray"),
                padding="4",
                spacing="2",
                bg="navy",
                color="white",
                width="full"
            ),
            spacing="0",
            width="full"
        ),
        width="96",
        class_name="overflow-hidden shadow-xl"
    )
def action_buttons() -> rx.Component:
    return rx.hstack(
        rx.button(
            rx.icon("arrow-left"),
            bg="transparent",
            color="yellow",
            class_name="rounded-full p-2 hover:bg-gray-800"
        ),
        rx.button(
            rx.icon("x"),
            bg="transparent",
            color="red",
            class_name="rounded-full p-2 hover:bg-gray-800"
        ),
        rx.button(
            rx.icon("star"),
            bg="transparent",
            color="lightblue",
            class_name="rounded-full p-2 hover:bg-gray-800"
        ),
        rx.button(
            rx.icon("check"),
            bg="transparent",
            color="green",
            class_name="rounded-full p-2 hover:bg-gray-800"
        ),
        rx.button(
            rx.icon("eye"), 
            bg="transparent",
            color="orange",
            class_name="rounded-full p-2 hover:bg-gray-800"
        ),
        spacing="2",
        justify="center",
        padding_y="4"
    )

def match_page() -> rx.Component:
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
app.add_page(match_page)