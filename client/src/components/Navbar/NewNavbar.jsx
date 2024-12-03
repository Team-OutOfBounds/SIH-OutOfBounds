import React, { useState } from 'react';
import { useAuth0 } from "@auth0/auth0-react";
import { Navbar, NavbarBrand, NavbarContent, NavbarItem, Button, Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Avatar, Switch } from "@nextui-org/react";
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';

import { SunIcon, MoonIcon } from 'lucide-react';
import { toggleTheme } from '../../store/themeSlice';
function NewNavBar() {
    const { user, isAuthenticated, loginWithRedirect, logout } = useAuth0();
    const [language, setLanguage] = useState('en');

    const dispatch = useDispatch();
    const isDarkMode = useSelector((state) => state.theme.isDarkMode);

    const handleToggle = () => {
        dispatch(toggleTheme());
    };

    const logoutWithRedirect = () =>
        logout({
            logoutParams: {
                returnTo: window.location.origin,
            },
        });

    const toggleLanguage = () => {
        const newLang = language === 'en' ? 'hi' : 'en';
        setLanguage(newLang);
    };

    return (
        <Navbar isBordered >
            <NavbarBrand>
                <img alt="Logo" src="../src/assets/logoNB.png" className="h-8 w-8 mr-2" />
                <p className="font-bold text-inherit">OutOfBounds</p>
            </NavbarBrand>

            <NavbarContent className={`hidden sm:flex gap-4`} justify="center">
                <NavbarItem>
                    <Link color="foreground" to="/">
                        {'Home'}
                    </Link>
                </NavbarItem>
                <NavbarItem>
                    <Link color="foreground" to="/recommend">
                        {'Recommend'}
                    </Link>
                </NavbarItem>
                <NavbarItem>
                    <Link color="foreground" to="/resources">
                        {'Resources'}
                    </Link>
                </NavbarItem>
                <NavbarItem>
                    <Link color="foreground" to="/contact">
                        {'Contact us'}
                    </Link>
                </NavbarItem>
            </NavbarContent>

            <NavbarContent justify="end">
                <NavbarItem>
                    <Switch
                        defaultSelected={isDarkMode}
                        size="lg"
                        color="primary"
                        startContent={<SunIcon />}
                        endContent={<MoonIcon />}
                        onChange={handleToggle}
                    />
                </NavbarItem>
                <NavbarItem>
                    <Button
                        color="primary"
                        variant="flat"
                        onClick={toggleLanguage}
                    >
                        {language === 'en' ? 'हिंदी' : 'English'}
                    </Button>
                </NavbarItem>
                {!isAuthenticated ? (
                    <NavbarItem>
                        <Button color="primary" variant="flat" onClick={() => loginWithRedirect()}>
                            {'Login'}
                        </Button>
                    </NavbarItem>
                ) : (
                    <Dropdown className='text-foreground bg-background' placement="bottom-end" classNames={{
                        content: "border-small border-divider bg-background",
                    }}>
                        <DropdownTrigger>
                            <Avatar
                                isBordered
                                as="button"
                                className="transition-transform"
                                color="primary"
                                name={user.name}
                                size="sm"
                                src={user.picture}
                            />
                        </DropdownTrigger>
                        <DropdownMenu aria-label="Profile Actions" variant="flat">
                            <DropdownItem key="signinas" className="h-14 gap-2 cursor-default">
                                <p className="font-semibold">{'Signed in as'}</p>
                                <p className="font-semibold">{user.email}</p>
                            </DropdownItem>
                            <DropdownItem key="profile" as={Link} href="/profile">
                                {'Profile'}
                            </DropdownItem>
                            <DropdownItem key="logout" color="danger" onClick={() => logoutWithRedirect()}>
                                {'Log Out'}
                            </DropdownItem>
                        </DropdownMenu>
                    </Dropdown>
                )}
            </NavbarContent>
        </Navbar>
    );
}

export default NewNavBar;

