import { useState } from "react";
import { logout, useNumCredits } from "../redux/UserSlice";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  billingPath,
  apiKeyDashboardPath,
  downloadPrivateGPTPath,
} from "../constants/RouteConstants";
import { Dropdown, Avatar } from "flowbite-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCoins } from "@fortawesome/free-solid-svg-icons";
import { useUser } from "../redux/UserSlice";
import LoginModal from "./LoginModal";

export function MainNav({ isLoggedIn, setIsLoggedInParent }) {
  const [showLoginModal, setShowLoginModal] = useState();
  let user = useUser();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  let numCredits = useNumCredits();
  let imageUrl = null;
  if (user && "profile_pic_url" in user) {
    imageUrl = user["profile_pic_url"];
  }

  function handleLogout() {
    dispatch(logout()).then(() => {
      navigate("/");
      setIsLoggedInParent(false);
    });
  }

  return (
    <div
      className={`fixed ${
        isLoggedIn && "md:pl-72"
      } z-50 flex items-center justify-between w-full px-2 py-4 text-white`}
    >
      {showLoginModal && (
        <LoginModal
          onClose={() => setShowLoginModal((p) => !p)}
          isOpen={showLoginModal}
        />
      )}
      <div className={"flex items-center"}>
        <button className="flex" onClick={() => navigate("/")}>
          <img alt="pancea logo" className={isLoggedIn && "hidden"} width={30} height={30} src="/logonew.png" />
          <span className="self-center whitespace-nowrap text-lg font-semibold text-white pl-2">
            Panacea
          </span>
        </button>
      </div>
      <button
        onClick={() => setShowLoginModal(true)}
        className={`py-2 ${
          isLoggedIn && "hidden"
        } px-4 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black rounded-lg font-medium hover:opacity-90 transition-opacity`}
      >
        Log In
      </button>
      <div className={`${!isLoggedIn && "hidden"} flex`}>
        <div
          className="mr-3 my-1 py-1 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black rounded-2xl cursor-pointer"
          onClick={() => navigate(downloadPrivateGPTPath)}
        >
          <span className="px-3 text-xs font-bold text-black">
            <FontAwesomeIcon icon={faCoins} className="mr-1" />
            Download Private Version
          </span>
        </div>
        <Dropdown
          theme={{
            arrowIcon: "text-white ml-2 h-4 w-4",
          }}
          className={`bg-gray-950 text-white`}
          inline
          label={
            imageUrl === "" ? (
              <Avatar rounded />
            ) : (
              <Avatar img={imageUrl} rounded />
            )
          }
        >
          <Dropdown.Header>
            {user && user.name && (
              <span className="block text-sm text-white">{user.name}</span>
            )}
            <span className="block truncate text-sm font-medium text-white hover:bg-[#141414]">
              {numCredits} Credits Remaining
              <FontAwesomeIcon icon={faCoins} className="ml-2" />
            </span>
          </Dropdown.Header>
          <Dropdown.Item
            onClick={() => navigate(billingPath)}
            className="text-white hover:text-black"
          >
            Billing
          </Dropdown.Item>
          <Dropdown.Item
            onClick={() => navigate(apiKeyDashboardPath)}
            className="text-white hover:text-black"
          >
            API
          </Dropdown.Item>
          <Dropdown.Divider />
          <Dropdown.Item
            onClick={() => handleLogout()}
            className="text-white hover:text-black"
          >
            Sign out
          </Dropdown.Item>
        </Dropdown>
      </div>
    </div>
  );
}

export default MainNav;
